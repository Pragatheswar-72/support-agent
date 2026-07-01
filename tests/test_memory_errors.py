import pytest

from src.errors import call_with_retry
from src.memory import ConversationMemory


def test_memory_add_turn_and_context_note():
    memory = ConversationMemory()
    assert memory.context_note() == ""

    memory.add_turn("where is order 1001?", "It was delivered.")
    assert len(memory.turns) == 2

    memory.update_last_order_id([{"agent": "order", "tool": "get_order_status", "args": {"order_id": 1001}, "result": {"order_id": 1001, "status": "delivered"}}])
    assert memory.last_order_id == 1001
    assert "order 1001" in memory.context_note()


def test_memory_last_order_id_from_result_when_no_args():
    memory = ConversationMemory()
    memory.update_last_order_id([{"agent": "refund", "tool": "check_refund_eligibility", "args": {}, "result": {"order_id": 1004, "eligible": False}}])
    assert memory.last_order_id == 1004


def test_call_with_retry_succeeds_first_try():
    result, escalation = call_with_retry(
        lambda: {"ok": True}, escalate_reason="n/a", escalate_context="n/a"
    )
    assert result == {"ok": True}
    assert escalation is None


def test_call_with_retry_escalates_after_exhausting_attempts():
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        raise RuntimeError("simulated rate limit")

    result, escalation = call_with_retry(
        flaky,
        max_attempts=2,
        backoff_seconds=0,
        escalate_reason="forced failure",
        escalate_context="test message",
    )
    assert result is None
    assert escalation["escalated"] is True
    assert "ticket_id" in escalation
    assert attempts["count"] == 2
