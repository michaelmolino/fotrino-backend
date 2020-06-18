from minio import Minio
from minio.error import BucketAlreadyOwnedByYou, AccessDenied

from util.env import (
                      FOTRINO_MINIO_HOST,
                      FOTRINO_MINIO_KEY,
                      FOTRINO_MINIO_SECRET,
                      FOTRINO_MINIO_SECURE,
                      FOTRINO_MINIO_REGION,
                      FOTRINO_MINIO_BUCKET
                     )


minio = Minio(FOTRINO_MINIO_HOST,
              access_key=FOTRINO_MINIO_KEY,
              secret_key=FOTRINO_MINIO_SECRET,
              secure=(FOTRINO_MINIO_SECURE),
              region=FOTRINO_MINIO_REGION)

try:
    minio.make_bucket(FOTRINO_MINIO_BUCKET)
except BucketAlreadyOwnedByYou:
    pass
except AccessDenied:
    pass
