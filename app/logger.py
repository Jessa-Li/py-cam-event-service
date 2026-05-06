import json
import logging
import sys
from flask import g, has_request_context

class JSONFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if has_request_context() and hasattr(g, "request_id"):
            payload["request_id"] = g.request_id
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for k, v in record.__dict__.items():
            if k.startswith("ctx_"):
                payload[k[4:]] = v
        return json.dumps(payload)

def configure_logging(app):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.DEBUG if app.config.get("DEBUG") else logging.INFO)