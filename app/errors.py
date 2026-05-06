from flask import jsonify, g, current_app
from werkzeug.exceptions import HTTPException, TooManyRequests

class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "app_error"):
        self.message = message
        self.status_code = status_code
        self.code = code

def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(e: AppError):
        return jsonify(error=e.code, message=e.message, request_id=g.request_id), e.status_code

    @app.errorhandler(TooManyRequests)
    def handle_rate_limit(e: TooManyRequests):
        # Flask-Limiter raises TooManyRequests; map it to our error shape so
        # clients see the same JSON envelope as every other failure.
        return (
            jsonify(error="rate_limited", message=str(e.description), request_id=g.request_id),
            429,
        )

    @app.errorhandler(HTTPException)
    def handle_http_error(e: HTTPException):
        return (
            jsonify(error="http_error", message=e.description, request_id=g.request_id),
            e.code or 500,
        )

    @app.errorhandler(Exception)
    def handle_unexpected(e: Exception):
        current_app.logger.exception("unhandled error", extra={"request_id": g.request_id})
        return (
            jsonify(error="internal_error", message="something went wrong", request_id=g.request_id),
            500,
        )