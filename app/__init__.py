from flask import Flask, g, request
import uuid

from .config import DevelopmentConfig, ProductionConfig, TestingConfig
from .extensions import db, migrate, cache, jwt, limiter
from .errors import register_error_handlers
from .logger import configure_logging
from .observability import init_tracing

CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

def create_app(env: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(CONFIG_MAP[env])

    configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    from .auth import auth_bp, register_cli
    from .blueprints.health import health_bp
    from .blueprints.cameras import cameras_bp
    from .blueprints.events import events_bp
    from .blueprints.alerts import alerts_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(cameras_bp, url_prefix="/cameras")
    app.register_blueprint(events_bp, url_prefix="/events")
    app.register_blueprint(alerts_bp, url_prefix="/alerts")

    register_cli(app)
    register_error_handlers(app)

    # Tracing comes last so all blueprints/extensions are registered before
    # the Flask instrumentor wraps the app. No-op when OTEL is disabled.
    init_tracing(app)

    @app.before_request
    def add_request_id():
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    @app.after_request
    def eho_request_id(response):
        response.headers["X-Request-ID"] = g.request_id
        return response

    return app