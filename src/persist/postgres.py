from persist.ConnectionPool import ConnectionPool

from yoyo import read_migrations
from yoyo import get_backend

from contextlib import contextmanager


from util.env import (
                      FOTRINO_POSTGRES_HOST,
                      FOTRINO_POSTGRES_PORT,
                      FOTRINO_POSTGRES_USER,
                      FOTRINO_POSTGRES_PASS,
                      FOTRINO_POSTGRES_DB
                     )

backend = get_backend('postgres://' + FOTRINO_POSTGRES_USER + ':' + FOTRINO_POSTGRES_PASS + '@' + FOTRINO_POSTGRES_HOST + ':' + FOTRINO_POSTGRES_PORT + '/' + FOTRINO_POSTGRES_DB)
migrations = read_migrations('./persist/migrations')
with backend.lock():
    backend.apply_migrations(backend.to_apply(migrations))

dbpool = ConnectionPool(4, 4,
                        host=FOTRINO_POSTGRES_HOST,
                        port=FOTRINO_POSTGRES_PORT,
                        user=FOTRINO_POSTGRES_USER,
                        password=FOTRINO_POSTGRES_PASS,
                        database=FOTRINO_POSTGRES_DB
                        )


@contextmanager
def getcursor():
    con = dbpool.getconn()
    try:
        yield con.cursor()
    finally:
        con.commit()
        dbpool.putconn(con)
