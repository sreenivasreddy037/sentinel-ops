"""Opt-in metadata-only Langfuse spans. No tickets, contexts, reports or notes."""

import logging

from app.config import Settings

logger = logging.getLogger(__name__)


class Telemetry:
    def __init__(self, settings: Settings):
        self.client = None
        if settings.langfuse_public_key and settings.langfuse_secret_key:
            from langfuse import Langfuse

            self.client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key.get_secret_value(),
                host=settings.langfuse_host,
            )

    def record(self, thread_id: str, status: str, retries: int, elapsed_ms: float):
        logger.info("incident_transition thread=%s status=%s retries=%d elapsed_ms=%.1f",
                    thread_id, status, retries, elapsed_ms)
        if self.client:
            try:
                with self.client.start_as_current_observation(name="sentinel-transition") as span:
                    span.update(metadata={"thread_id": thread_id, "status": status,
                                          "retry_count": retries, "elapsed_ms": elapsed_ms,
                                          "mode": "simulation"})
            except Exception:
                # Observability must not invalidate an already committed approval.
                logger.warning("Optional telemetry delivery failed")

    def close(self):
        if self.client:
            self.client.flush()
