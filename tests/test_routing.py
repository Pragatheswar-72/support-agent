import pytest

from src import orchestrator


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    def __init__(self, response_text):
        self.response_text = response_text

    def invoke(self, _prompt):
        return FakeMessage(self.response_text)


@pytest.mark.parametrize(
    "raw_response,expected",
    [
        ("ORDER", "ORDER"),
        ("refund", "REFUND"),
        ("  Payment  ", "PAYMENT"),
        ("I think this is FAQ related", "FAQ"),
        ("this is unclear and abusive", "ESCALATE"),
        ("something totally unrelated", "ESCALATE"),
    ],
)
def test_parse_route(raw_response, expected):
    assert orchestrator.parse_route(raw_response) == expected


@pytest.mark.parametrize(
    "user_message,fake_route,expected_agent",
    [
        ("Where is order 1001?", "ORDER", "order"),
        ("I want a refund for order 1004", "REFUND", "refund"),
        ("Has my payment gone through?", "PAYMENT", "payment"),
        ("What's your return policy?", "FAQ", "faq"),
        ("asdkjhasd nonsense", "ESCALATE", "escalate"),
    ],
)
def test_orchestrator_routes_to_correct_agent(monkeypatch, user_message, fake_route, expected_agent):
    monkeypatch.setattr(orchestrator, "get_llm", lambda: FakeLLM(fake_route))

    fake_result = {"reply": "stub reply", "trace": [], "agent": expected_agent}
    for name in ("run_order_agent", "run_refund_agent", "run_payment_agent", "run_faq_agent"):
        monkeypatch.setattr(orchestrator, name, lambda *_a, **_k: fake_result)

    graph = orchestrator.build_graph()
    result = graph.invoke({"user_message": user_message, "history": [], "trace": []})

    assert result["agent"] == expected_agent
    if expected_agent != "escalate":
        assert result["reply"] == "stub reply"
    else:
        assert result["reply"]  # escalate_to_human's real message
