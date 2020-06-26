from models.album import Album

from persist.postgres import getcursor
from flask_login import UserMixin
from flask_wtf.csrf import generate_csrf


class User(UserMixin):
    def __init__(self, id, identity_provider, external_id, name, email, profile_pic, country, csrf_token):
        self.id = int(id)
        self.identity_provider = identity_provider
        self.external_id = external_id
        self.name = name
        self.email = email
        self.profile_pic = profile_pic
        self.country = country
        self.csrf_token = csrf_token

    @staticmethod
    def get(id):
        with getcursor() as cur:
            cur.execute(
                "SELECT identity_provider, external_id, name, email, profile_pic, country FROM users WHERE id = %s", (id,)
            )
            row = cur.fetchone()
        if not row:
            return None

        user = User(
            id=id, identity_provider=row[0], external_id=row[1], name=row[2], email=row[3], profile_pic=row[4], country=row[5], csrf_token=generate_csrf()
        )
        return user

    @staticmethod
    def get_user_from_email(email):
        with getcursor() as cur:
            cur.execute(
                "SELECT id, identity_provider, external_id, name, profile_pic, country FROM users WHERE email = %s", (email,)
            )
            row = cur.fetchone()
        if not row:
            return None
        user = User(
            id=row[0], identity_provider=row[1], external_id=row[2], name=row[3], email=email, profile_pic=row[4], country=row[5], csrf_token=generate_csrf()
        )
        return user

    @staticmethod
    def create(identity_provider, external_id, name, email, profile_pic, country):
        with getcursor() as cur:
            cur.execute(
                "INSERT INTO users (identity_provider, external_id, name, email, profile_pic, country, last_login, created)"
                " VALUES (%s, %s, %s, %s, %s, %s, current_timestamp, current_timestamp)"
                " RETURNING id",
                (identity_provider, external_id, name, email, profile_pic, country,)
            )
            user_id = cur.fetchone()[0]
        user = User(user_id, identity_provider, external_id, name, email, profile_pic, country, generate_csrf())
        Album.create(user, "Unsorted")
        return user
