import os

# Environment
FOTRINO_SECRET_KEY = os.environ.get("FOTRINO_SECRET_KEY") or os.urandom(24)
FOTRINO_OAUTH_PROVIDERS = (os.environ.get("FOTRINO_OAUTH_PROVIDERS") or "Hydra").split(',')
FOTRINO_POSTGRES_HOST = os.environ.get("FOTRINO_POSTGRES_HOST") or '127.0.0.1'
FOTRINO_POSTGRES_PORT = os.environ.get("FOTRINO_POSTGRES_PORT") or '5432'
FOTRINO_POSTGRES_USER = os.environ.get("FOTRINO_POSTGRES_USER") or 'fotrino'
FOTRINO_POSTGRES_PASS = os.environ.get("FOTRINO_POSTGRES_PASS") or 'fotrino'
FOTRINO_POSTGRES_DB = os.environ.get("FOTRINO_POSTGRES_DB") or 'fotrino'
FOTRINO_MINIO_HOST = os.environ.get("FOTRINO_MINIO_HOST") or '127.0.0.1:9000'
FOTRINO_MINIO_KEY = os.environ.get("FOTRINO_MINIO_KEY") or 'minioadmin'
FOTRINO_MINIO_SECRET = os.environ.get("FOTRINO_MINIO_SECRET") or 'minioadmin'
FOTRINO_MINIO_SECURE = (os.environ.get("FOTRINO_MINIO_SECURE") or 'False') == 'True'
FOTRINO_MINIO_REGION = os.environ.get("FOTRINO_MINIO_REGION") or 'us-east-1'
FOTRINO_MINIO_BUCKET = os.environ.get("FOTRINO_MINIO_BUCKET") or 'fotrino'
FOTRINO_REDIS_HOST = os.environ.get("FOTRINO_REDIS_HOST") or '127.0.0.1'
FOTRINO_REDIS_PORT = os.environ.get("FOTRINO_REDIS_PORT") or '6379'
FOTRINO_REDIS_DB = os.environ.get("FOTRINO_REDIS_DB") or '0'
FOTRINO_HYDRA_HOST = os.environ.get("FOTRINO_HYDRA_HOST") or "127.0.0.1:4444"
