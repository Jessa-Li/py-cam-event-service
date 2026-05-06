import os
from datetime import timedelta

class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    JWT_SECRET_TOKEN = os.environ.get("JWT_SECRET_TOKEN", SECRET_KEY)
    # 8h matches a typical work-day session. Clients (mobile / web) store the
    # token in a secure-enough place for their platform (Keychain / Keystore /
    # localStorage) and re-login when it expires.
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    SQLALCHEMY_TRACK_NOTIFICATIONS = False
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 30

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/cameras")
    # In dev, share Redis with caching if it's set; otherwise in-process memory.
    RATELIMIT_STORAGE_URI = os.environ.get("REDIS_URL", "memory://")

class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]
    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_URL = os.environ["REDIS_URL"]
    # Must be Redis (or another shared store) — memory:// would let an
    # attacker hop between gunicorn workers to get N× the limit.
    RATELIMIT_STORAGE_URI = os.environ["REDIS_URL"]
    PREFERRED_URL_SCHEME = "https"

class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    CACHE_TYPE = "NullCache"
    # Off by default in tests so unrelated tests don't trip limits;
    # tests that exercise rate limiting flip this on explicitly.
    RATELIMIT_ENABLED = False
    RATELIMIT_STORAGE_URI = "memory://"