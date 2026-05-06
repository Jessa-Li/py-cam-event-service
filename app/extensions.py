from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache
from flask_jwt_extended import JWTManager, get_jwt_identity, verify_jwt_in_request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
cache = Cache()
jwt = JWTManager()


def rate_limit_key():
    """Key by JWT identity when present, else by IP. Cameras live behind NAT
    so IP-only would lump every device on the same home network into one
    bucket; JWT identity (the camera or admin) is the right granularity."""
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            return f"jwt:{identity}"
    except Exception:
        pass
    return get_remote_address()


# Default applies to every route; per-route decorators override with tighter
# or looser limits where it matters (login = brute-force, events = camera spam).
limiter = Limiter(
    key_func=rate_limit_key,
    default_limits=["200 per minute"],
)