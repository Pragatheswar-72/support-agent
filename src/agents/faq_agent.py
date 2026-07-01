from langchain_core.tools import tool

from src import tools as backend_tools
from src.agents.base import run_tool_agent


@tool
def answer_faq(question: str) -> str:
    """Answer a general policy question (shipping, returns, cancellations, refunds, contact info)."""
    return backend_tools.answer_faq(question)


FAQ_TOOLS = [answer_faq]

SYSTEM_PROMPT = (
    "You are the FAQ Agent for an e-commerce support system, answering general policy questions "
    "about shipping, returns, cancellations, refunds, and how to contact support. "
    "Always call answer_faq to get the official policy text before answering; never guess. "
    "Reply concisely and naturally to the customer."
)

# FAQ answers are deterministic policy text, so identical questions are cached
# to skip a repeat LLM call entirely (saves quota + latency).
_faq_cache: dict[str, dict] = {}


def run_faq_agent(user_message: str, history: list | None = None) -> dict:
    cache_key = user_message.strip().lower()
    cached = _faq_cache.get(cache_key)
    if cached is not None:
        return {**cached, "cached": True, "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}

    result = run_tool_agent("faq", SYSTEM_PROMPT, FAQ_TOOLS, user_message, history)
    _faq_cache[cache_key] = result
    return {**result, "cached": False}
