from persist.postgres import getcursor
from persist.minio import minio
from util.cache import cache
from models.album import Album
from models.user import User
from util.env import FOTRINO_MINIO_BUCKET


import os
import json
import distance
from datetime import timedelta, datetime

from psycopg2.errors import UniqueViolation, InvalidTextRepresentation

ALLOWED_EXTENSIONS = set(['.jpg', '.jpeg', '.arw', '.srf', '.sr2', '.crw', '.cr2', '.cr3', '.nef', '.nrw', '.pef', '.ptx'])

CACHE_CONTROL_HEADER = 'public, max-age=86400, immutable'


class Photo():
    def __init__(self, id, owner, album, hash, extension, flag, exif_datetime, thumbnail_url, fullsize_url, original_url):
        self.id = int(id)
        self.owner = int(owner)
        if album:
            self.album = int(album)
        else:
            album = None
        self.hash = hash
        self.extension = extension
        self.flag = flag
        self.exif_datetime = json.dumps(exif_datetime, indent=4, sort_keys=True, default=str)
        self.thumbnail_url = thumbnail_url
        self.fullsize_url = fullsize_url
        self.original_url = original_url

    @staticmethod
    def allowed_file(filename):
        file_name, file_extension = os.path.splitext(filename)
        return file_extension.lower() in ALLOWED_EXTENSIONS

    # TODO if status is not P but it exists, restore it.
    @staticmethod
    def exists(user, hash):
        with getcursor() as cur:
            cur.execute(
                "SELECT 1 FROM photos WHERE owner = %s AND hash = %s AND status IN ('P', 'R', 'U')",
                (user.id, hash,)
            )
            exists = cur.rowcount == 1
        return exists

    @staticmethod
    def get(user, id):
        with getcursor() as cur:
            cur.execute(
                "SELECT album, hash, extension, flag, exif_datetime FROM photos WHERE owner = %s AND id = %s AND status IN ('P', 'R', 'U')",
                (user.id, id,)
            )
            if not cur.rowcount == 1:
                raise ValueError("Photo not found.")
            row = cur.fetchone()
        thumbnail_url = Photo.get_presigned_url_tn(user, row[1])
        fullsize_url = Photo.get_presigned_url_fs(user, row[1])
        original_url = Photo.get_presigned_url_original(user, row[1], row[2])
        return Photo(id, user.id, row[0], row[1], row[2], row[3], row[4], thumbnail_url, fullsize_url, original_url)

    def update(self, user, album, flag, exif_datetime):
        with getcursor() as cur:
            cur.execute(
                "UPDATE photos SET album = %s, flag = %s, exif_datetime = %s WHERE owner = %s AND id = %s",
                (album, flag, exif_datetime, user.id, self.id,)
            )
            if not cur.rowcount == 1:
                raise ValueError("Unable to update photo.")
        self.album = album
        self.exif_datetime = exif_datetime
        return self

    @staticmethod
    def get_presigned_put_url(user, hash, filename):
        file_name, file_extension = os.path.splitext(filename)
        object_name = str(user.id) + "/original/" + hash[:2] + "/" + hash + file_extension
        url = minio.presigned_put_object(FOTRINO_MINIO_BUCKET, object_name, expires=timedelta(days=1))
        return url

    @staticmethod
    def create(user, album, hash, file, exif_datetime):
        needs_update = False
        file_name, file_extension = os.path.splitext(file)
        if not exif_datetime:
            exif_datetime = "1930:08:25 12:00:00"
        exif_datetime = datetime.strptime(exif_datetime, "%Y:%m:%d %H:%M:%S")
        destination_album = None
        with getcursor() as cur:
            if album:
                destination_album = Album.get(user, album)
            if not destination_album:
                destination_album = Album.get_album_by_name(user, "Unsorted")
            try:
                cur.execute(
                    "INSERT INTO photos (owner, album, hash, extension, exif_datetime, created)"
                    " VALUES (%s, %s, %s, %s, %s, current_timestamp)"
                    " RETURNING id",
                    (user.id, destination_album.id, hash, file_extension, exif_datetime)
                )
                photo_id = cur.fetchone()[0]
            except UniqueViolation:
                needs_update = True
            if needs_update:
                with getcursor() as cur:
                    cur.execute(
                        "UPDATE photos SET album = %s, exif_datetime = %s, flag = NULL, status = 'P'"
                        " WHERE owner = %s AND hash = %s"
                        " RETURNING id",
                        (destination_album.id, exif_datetime, user.id, hash)
                    )
                    photo_id = cur.fetchone()[0]
        thumbnail_url = Photo.get_presigned_url_tn(user, hash)
        fullsize_url = Photo.get_presigned_url_fs(user, hash)
        original_url = Photo.get_presigned_url_original(user, hash, file_extension)
        return Photo(photo_id, user.id, album, hash, file_extension, None, exif_datetime, thumbnail_url, fullsize_url, original_url)

    @staticmethod
    @cache.memoize(64800)
    def get_presigned_url_tn(user, hash):
        object_name = str(user.id) + "/thumbnail/" + hash[:2] + "/" + hash + ".jpeg"
        return minio.presigned_get_object(FOTRINO_MINIO_BUCKET, object_name, expires=timedelta(days=1), response_headers={'response-Cache-Control': CACHE_CONTROL_HEADER})

    @staticmethod
    @cache.memoize(64800)
    def get_presigned_url_fs(user, hash):
        object_name = str(user.id) + "/large/" + hash[:2] + "/" + hash + ".jpeg"
        return minio.presigned_get_object(FOTRINO_MINIO_BUCKET, object_name, expires=timedelta(days=1), response_headers={'response-content-disposition': 'attachment', 'response-Cache-Control': CACHE_CONTROL_HEADER, 'response-Content-Type': 'image/jpeg', 'response-X-Content-Type-Options': 'nosniff'})

    @staticmethod
    @cache.memoize(64800)
    def get_presigned_url_original(user, hash, extension):
        object_name = str(user.id) + "/original/" + hash[:2] + "/" + hash + extension
        return minio.presigned_get_object(FOTRINO_MINIO_BUCKET, object_name, expires=timedelta(days=1), response_headers={'response-content-disposition': 'attachment', 'response-Cache-Control': CACHE_CONTROL_HEADER})

    @staticmethod
    def get_photos(user, album):
        photos = []
        with getcursor() as cur:
            cur.execute(
                "SELECT id FROM photos WHERE owner = %s AND album = %s AND status IN ('P', 'R', 'U') ORDER BY exif_datetime ASC",
                (user.id, album,)
            )
            rows = cur.fetchall()
            for row in rows:
                photos.append(Photo.get(user, row[0]))
        return photos

    @staticmethod
    def get_shared_photos(album_uuid):
        photos = []
        with getcursor() as cur:
            try:
                cur.execute(
                    "SELECT photos.owner, photos.id "
                    "FROM photos, albums "
                    "WHERE photos.album = albums.id AND photos.owner = albums.owner and "
                    "   albums.uuid = %s AND albums.shared=true AND status IN ('P', 'R', 'U') AND flag = 'P' "
                    "ORDER BY exif_datetime ASC",
                    (album_uuid,)
                )
                rows = cur.fetchall()
            except InvalidTextRepresentation:
                raise ValueError("Invalid album ID.")
            try:
                user = User.get(rows[0][0])
            except IndexError:
                raise ValueError("Invalid album ID or no photos in this album.")
            for row in rows:
                photos.append(Photo.get(user, row[1]))
        return photos

    @staticmethod
    def get_similar_photos(user, album):
        with getcursor() as cur:
            cur.execute(
                "SELECT phash, id FROM photos WHERE owner = %s AND album = %s AND phash IS NOT NULL ORDER BY phash", (user.id, album,)
            )
            rows = cur.fetchall()
        # TODO clusters should be cached based on rows as a key ie. if the photos haven't changed, the clustering won't have changed
        clusters = []
        for phash, id in (rows):
            found = False
            for cluster in clusters:
                for photo in cluster:
                    if distance.hamming(photo['phash'], phash) <= 8:
                        # add photo to an existing cluster
                        cluster.append({"phash": phash, "id": id})
                        # stop looking once first cluster is found
                        found = True
                        break
                if found:
                    break
            # start a new cluster
            clusters.append([{"phash": phash, "id": id}])
        return list(filter(lambda x: len(x) > 1, clusters))

    @staticmethod
    def delete(user, id):
        with getcursor() as cur:
            # TODO No way to undelete
            cur.execute(
                "UPDATE photos SET status = 'D' WHERE owner = %s AND id = %s",
                (user.id, id,)
            )
            if not cur.rowcount == 1:
                raise ValueError("Unable to delete photo.")

    @staticmethod
    def get_exif(user, id):
        exif = []
        with getcursor() as cur:
            cur.execute(
                "SELECT tag, value FROM photo_metadata WHERE owner = %s and photo = %s ORDER BY id",
                (user.id, id)
            )
            rows = cur.fetchall()
        for row in rows:
            exif.append({'key': row[0], 'value': row[1]})
        return exif
