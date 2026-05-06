"""OpenTelemetry tracing setup.

Configures a TracerProvider that exports spans via OTLP/HTTP to Jaeger
(or any OTLP-compatible collector). Auto-instruments Flask, SQLAlchemy,
Redis, and outbound `requests` calls.

Configuration is via standard OTEL_* environment variables:
  - OTEL_SERVICE_NAME            (e.g. "cam-event-service")
  - OTEL_EXPORTER_OTLP_ENDPOINT  (e.g. "http://jaeger:4318")
  - OTEL_TRACES_SAMPLER          (default "parentbased_always_on")
  - OTEL_SDK_DISABLED            ("true" to skip setup entirely)

Tracing is a no-op when OTEL_SDK_DISABLED=true or when no endpoint is set,
so tests and local runs without Jaeger don't pay any cost or fail noisily.
"""

from __future__ import annotations

import logging
import os

from flask import Flask

logger = logging.getLogger(__name__)

_initialized = False


def init_tracing(app: Flask) -> None:
    """Initialize OpenTelemetry tracing for the given Flask app.

    Safe to call multiple times — instrumentation is applied once per process.
    """
    global _initialized

    if os.environ.get("OTEL_SDK_DISABLED", "").lower() == "true":
        logger.info("OpenTelemetry disabled via OTEL_SDK_DISABLED")
        return

    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        logger.info("OTEL_EXPORTER_OTLP_ENDPOINT not set; skipping tracing setup")
        return

    if _initialized:
        # Re-instrument the new Flask app instance, but don't reconfigure the
        # global provider — that would duplicate spans.
        _instrument_flask(app)
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    service_name = os.environ.get("OTEL_SERVICE_NAME", "cam-event-service")
    resource = Resource.create({"service.name": service_name})

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    _instrument_flask(app)
    _instrument_sqlalchemy(app)
    _instrument_redis()
    _instrument_requests()
    _instrument_logging()

    _initialized = True
    logger.info(
        "OpenTelemetry tracing initialized (service=%s, endpoint=%s)",
        service_name,
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"],
    )


def _instrument_flask(app: Flask) -> None:
    from opentelemetry.instrumentation.flask import FlaskInstrumentor

    FlaskInstrumentor().instrument_app(app)


def _instrument_sqlalchemy(app: Flask) -> None:
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    # The SQLAlchemy engine is created lazily by Flask-SQLAlchemy on first use.
    # Pushing an app context here forces engine creation so we can hand it to
    # the instrumentor — otherwise queries issued before the first request
    # would not be traced.
    from .extensions import db

    with app.app_context():
        engine = db.engine
    SQLAlchemyInstrumentor().instrument(engine=engine)


def _instrument_redis() -> None:
    from opentelemetry.instrumentation.redis import RedisInstrumentor

    RedisInstrumentor().instrument()


def _instrument_requests() -> None:
    from opentelemetry.instrumentation.requests import RequestsInstrumentor

    RequestsInstrumentor().instrument()


def _instrument_logging() -> None:
    # Injects trace_id / span_id into log records so logs can be correlated
    # with traces in Jaeger / log aggregators.
    from opentelemetry.instrumentation.logging import LoggingInstrumentor

    LoggingInstrumentor().instrument(set_logging_format=False)
