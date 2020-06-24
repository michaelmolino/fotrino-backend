from persist.postgres import getcursor
from persist.minio import minio
import io
from PIL import Image
from PIL.ExifTags import TAGS
import os
import imagehash
import rawpy
from datetime import datetime

RAW_EXTENSIONS = set(['.arw', '.srf', '.sr2', '.crw', '.cr2', '.cr3', '.nef', '.nrw', '.pef', '.ptx'])


# TODO it would be nice if uploading and hashing happened in parallel
def process_photo(bucket, object, id):
    owner, version, hash_prefix, filename = object.split('/')
    file_name, file_extension = os.path.splitext(filename)
    file_hash = filename.split('.')[0]
    photo = io.BytesIO(minio.get_object(bucket, object).read())

    if file_extension.lower() in RAW_EXTENSIONS:
        with rawpy.imread(photo) as raw:
            photo = io.BytesIO(raw.extract_thumb().data)

    try:
        with Image.open(photo) as p:
            if p.format not in set(["JPEG"]):
                raise ValueError(p.format, " is not supported.")

            large = io.BytesIO()
            p.thumbnail((4096, 4096))
            exif = p.info.get('exif') or b""
            p.save(large, "JPEG", exif=exif)
            size = large.tell()
            large.seek(0)
            large_object = "/".join([owner, "large", hash_prefix, file_name + ".jpeg"])
            minio.put_object(bucket, large_object, large, size, content_type='image/jpeg')
            large.close()

            thumbnail = io.BytesIO()
            p.thumbnail((256, 256))
            p.save(thumbnail, "JPEG", exif=exif)
            size = thumbnail.tell()
            thumbnail.seek(0)
            thumbnail_object = "/".join([owner, "thumbnail", hash_prefix, file_name + ".jpeg"])
            minio.put_object(bucket, thumbnail_object, thumbnail, size, content_type='image/jpeg')
            thumbnail.close()

            try:
                exif = p._getexif().items()
            except AttributeError:
                exif = None

            phash = imagehash.phash(p)
    except OSError:
        raise ValueError("Photo could not be opened.")

    with getcursor() as cur:
        for k, v in exif:
            tag = TAGS.get(k, k)
            cur.execute(
                "INSERT INTO photo_metadata (photo, owner, hash, tag, value) "
                "VALUES (%s, %s, %s, %s, %s)",
                (id, owner, file_hash, tag, str(v)[:255],)
            )
            if tag == 'DateTime':
                exif_datetime = datetime.strptime(v or "1930:08:25 12:00:00", "%Y:%m:%d %H:%M:%S")
                cur.execute(
                    "UPDATE photos SET exif_datetime = %s WHERE id = %s", (exif_datetime, id)
                )
        cur.execute(
            "UPDATE photos SET phash = %s WHERE id = %s AND owner = %s",
            (str(phash), id, owner,)
        )
        cur.execute(
            "UPDATE photos SET status = 'R' WHERE id = %s AND owner = %s",
            (id, owner,)
        )
