from fastapi.testclient import TestClient

import api

client = TestClient(api.app)

FAKE_RESULT = {
    "reply": "Your order 1001 has been delivered.",
    "agent": "order",
    "trace": [
        {
            "agent": "order",
            "tool": "get_order_status",
            "args": {"order_id": 1001},
            "result": {"order_id": 1001, "status": "delivered"},
        }
    ],
    "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    "cached": False,
}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_returns_agent_reply_and_trace(monkeypatch):
    monkeypatch.setattr(api, "run_orchestrator", lambda *_a, **_k: FAKE_RESULT)

    response = client.post("/chat", json={"message": "where is order 1001?"})

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Your order 1001 has been delivered."
    assert body["agent"] == "order"
    assert body["trace"][0]["tool"] == "get_order_status"
    assert body["usage"]["total_tokens"] == 15
    assert "session_id" in body


def test_chat_generates_new_session_id_when_omitted(monkeypatch):
    monkeypatch.setattr(api, "run_orchestrator", lambda *_a, **_k: FAKE_RESULT)

    r1 = client.post("/chat", json={"message": "hello"})
    r2 = client.post("/chat", json={"message": "hello again"})

    assert r1.json()["session_id"] != r2.json()["session_id"]


def test_chat_reuses_provided_session_id_and_carries_history(monkeypatch):
    captured_history = []

    def fake_orchestrator(user_message, history=None):
        captured_history.append(list(history or []))
        return FAKE_RESULT

    monkeypatch.setattr(api, "run_orchestrator", fake_orchestrator)

    r1 = client.post("/chat", json={"message": "where is order 1001?", "session_id": "abc123"})
    assert r1.json()["session_id"] == "abc123"

    r2 = client.post("/chat", json={"message": "refund it", "session_id": "abc123"})
    assert r2.json()["session_id"] == "abc123"

    # second call's history should include the first turn (memory persisted across requests)
    assert len(captured_history[0]) == 0
    assert len(captured_history[1]) == 2


def test_chat_rejects_empty_message():
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 422
