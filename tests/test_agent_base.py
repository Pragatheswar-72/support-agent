from langchain_core.tools import tool

from src.agents import base


class FakeToolCallMessage:
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeLLM:
    """Replays a scripted sequence of AIMessage-like responses."""

    def __init__(self, responses):
        self._responses = list(responses)
        self._i = 0

    def bind_tools(self, _tools):
        return self

    def invoke(self, _messages):
        msg = self._responses[min(self._i, len(self._responses) - 1)]
        self._i += 1
        return msg


@tool
def echo_tool(value: str) -> str:
    """Echoes back a value."""
    return f"echoed:{value}"


def test_run_tool_agent_returns_normal_reply(monkeypatch):
    responses = [
        FakeToolCallMessage(tool_calls=[{"name": "echo_tool", "args": {"value": "hi"}, "id": "1"}]),
        FakeToolCallMessage(content="Here is your answer."),
    ]
    monkeypatch.setattr(base, "get_llm", lambda: FakeLLM(responses))

    result = base.run_tool_agent("test", "system prompt", [echo_tool], "hello")

    assert result["reply"] == "Here is your answer."
    assert len(result["trace"]) == 1


def test_run_tool_agent_falls_back_when_model_never_answers(monkeypatch):
    # Model calls the same tool with the same args every round and never
    # produces closing text - reproduces the real bug seen with Groq/Llama
    # under long conversation history.
    stuck_response = FakeToolCallMessage(
        content="", tool_calls=[{"name": "echo_tool", "args": {"value": "x"}, "id": "1"}]
    )
    monkeypatch.setattr(base, "get_llm", lambda: FakeLLM([stuck_response] * 10))

    result = base.run_tool_agent("test", "system prompt", [echo_tool], "hello")

    assert result["reply"] == "echoed:x"  # falls back to the tool result, never blank
    assert len(result["trace"]) == 1  # loop-detection stopped after the first repeat


def test_run_tool_agent_stops_on_repeated_identical_call(monkeypatch):
    responses = [
        FakeToolCallMessage(tool_calls=[{"name": "echo_tool", "args": {"value": "a"}, "id": "1"}]),
        FakeToolCallMessage(tool_calls=[{"name": "echo_tool", "args": {"value": "a"}, "id": "2"}]),
        FakeToolCallMessage(content="should never get here"),
    ]
    monkeypatch.setattr(base, "get_llm", lambda: FakeLLM(responses))

    result = base.run_tool_agent("test", "system prompt", [echo_tool], "hello")

    assert len(result["trace"]) == 1
    assert result["reply"] == "echoed:a"
