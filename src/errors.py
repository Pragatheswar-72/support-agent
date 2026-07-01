import logging
import time

from src.tools import escalate_to_human

logger = logging.getLogger("support_agent.errors")


def call_with_retry(fn, *, max_attempts: int = 2, backoff_seconds: float = 3.0, escalate_reason: str, escalate_context: str):
    """Run fn(); on failure, retry once after a short backoff; if it still fails, escalate to a human
    instead of crashing. Returns (result, escalation) — exactly one of which is non-None."""
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(), None
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any agent/LLM failure should escalate, not crash
            last_exc = exc
            logger.warning("Attempt %d/%d failed: %s", attempt, max_attempts, exc)
            if attempt < max_attempts:
                time.sleep(backoff_seconds)

    escalation = escalate_to_human(reason=escalate_reason, context=f"{escalate_context} | error: {last_exc}")
    return None, escalation
