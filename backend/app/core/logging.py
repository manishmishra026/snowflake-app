import logging
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from app.core.config import settings

logger = logging.getLogger("app")

def setup_logging(app=None) -> None:
    """Set up Azure Monitor OpenTelemetry exporter for metrics, traces, and logging."""
    connection_string = settings.APPLICATIONINSIGHTS_CONNECTION_STRING.strip()

    if not connection_string:
        logger.info("APPLICATIONINSIGHTS_CONNECTION_STRING not set. Telemetry export disabled.")
        return

    try:
        logger.info("Configuring Azure Monitor OpenTelemetry exporter")
        configure_azure_monitor(
            connection_string=connection_string,
        )
        if app:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI HTTP endpoint logging instrumented successfully")
    except Exception as exc:
        logger.error("Failed to bootstrap Azure Monitor logging: %s", exc, exc_info=True)
