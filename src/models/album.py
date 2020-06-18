from persist.postgres import getcursor

import uuid


class Album():
    def __init__(self, id, owner, name, album_uuid=None, shared=False):
        self.id = int(id)
        self.owner = int(owner)
        self.name = name
        self.album_uuid = album_uuid
        self.shared = shared

    @staticmethod
    def get(user, id):
        with getcursor() as cur:
            cur.execute(
                "SELECT name, uuid, shared FROM albums WHERE owner = %s AND id = %s", (user.id, id,)
            )
            if not cur.rowcount == 1:
                raise ValueError("Album not found.")
            row = cur.fetchone()
        return Album(id, user.id, row[0], row[1], row[2])

    @staticmethod
    def get_album_by_name(user, name):
        with getcursor() as cur:
            cur.execute(
                "SELECT id, uuid, shared FROM albums WHERE owner = %s AND name = %s", (user.id, name,)
            )
            if not cur.rowcount == 1:
                raise ValueError("Album not found.")
            row = cur.fetchone()
        return Album(row[0], user.id, name, row[1], row[2])

    @staticmethod
    def get_all(user):
        albums = []
        with getcursor() as cur:
            cur.execute(
                "SELECT id, name, uuid, shared FROM albums WHERE owner = %s", (user.id,)
            )
            rows = cur.fetchall()
            for row in rows:
                albums.append(Album(row[0], user.id, row[1], row[2], row[3]))
        return albums

    @staticmethod
    def create(user, name):
        with getcursor() as cur:
            cur.execute(
                "INSERT INTO albums (owner, name, created) VALUES (%s, %s, current_timestamp)"
                " RETURNING id",
                (user.id, name,)
            )
            id = cur.fetchone()[0]
        return Album(id, user.id, name)

    def update(self, user, name):
        if name == "Unsorted":
            raise ValueError("Unsorted is a system folder and cannot be renamed.")
        with getcursor() as cur:
            cur.execute(
                "UPDATE albums SET name = %s WHERE owner = %s AND id = %s AND name != 'Unsorted'",
                (name, user.id, self.id,)
            )
            if not cur.rowcount == 1:
                raise ValueError("Unable to update album.")
        self.name = name
        return self

    def share(self, user, shared):
        if self.name == "Unsorted":
            raise ValueError("Unsorted cannot be shared.")
        if shared:
            album_uuid = str(uuid.uuid4())
        else:
            album_uuid = None
        print("debug:", shared, album_uuid)
        with getcursor() as cur:
            cur.execute(
                "UPDATE albums SET shared = %s, uuid = %s WHERE owner = %s AND id = %s AND name != 'Unsorted'",
                (shared, album_uuid, user.id, self.id,)
            )
            if not cur.rowcount == 1:
                raise ValueError("Unable to share album.")
        self.shared = shared
        self.album_uuid = album_uuid
        return self

    def delete(self, user):
        unsorted = Album.get_album_by_name(user, "Unsorted")
        print("DEBUG: " + str(unsorted.id) + " - " + str(self.id))
        if unsorted.id == self.id:
            raise ValueError("Unsorted is a system folder and cannot be deleted.")
        with getcursor() as cur:
            cur.execute(
                "UPDATE photos SET album = %s WHERE owner = %s AND album = %s", (unsorted.id, user.id, self.id,)
            )
            cur.execute(
                "DELETE FROM albums WHERE owner = %s AND id = %s",
                (user.id, self.id,)
            )
            if not cur.rowcount == 1:
                raise ValueError("Unable to delete album.")
