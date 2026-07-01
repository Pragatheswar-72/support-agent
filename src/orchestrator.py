import logging
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from src.agents.base import as_text, sum_usage
from src.agents.faq_agent import run_faq_agent
from src.agents.order_agent import run_order_agent
from src.agents.payment_agent import run_payment_agent
from src.agents.refund_agent import run_refund_agent
from src.errors import call_with_retry
from src.llm import extract_usage, get_llm
from src.logging_config import configure_logging
from src.tools import escalate_to_human

configure_logging()
logger = logging.getLogger("support_agent.orchestrator")

ROUTES = ("ORDER", "REFUND", "PAYMENT", "FAQ", "ESCALATE")

ROUTER_PROMPT = """You are a customer-support router. Read the user's message and decide which
specialist should handle it. Respond with ONLY one word from this list:
- ORDER    : order status, tracking, order details
- REFUND   : refund requests, refund status, eligibility
- PAYMENT  : payment status, making a payment
- FAQ      : general policy questions (shipping times, return policy)
- ESCALATE : anything unclear, abusive, or outside the above

User message: {user_message}
Answer with one word only."""


class SupportState(TypedDict):
    user_message: str
    history: list
    route: str
    reply: str
    trace: list
    agent: str
    usage: dict
    cached: bool


def parse_route(text: str) -> str:
    text = text.strip().upper()
    return next((r for r in ROUTES if r in text), "ESCALATE")


def route_node(state: SupportState) -> dict:
    llm = get_llm()
    result = llm.invoke(ROUTER_PROMPT.format(user_message=state["user_message"]))
    route = parse_route(as_text(result.content))
    return {"route": route, "usage": extract_usage(result)}


def _make_agent_node(agent_name: str, run_fn):
    def node(state: SupportState) -> dict:
        result = run_fn(state["user_message"], state.get("history"))
        return {
            "reply": result["reply"],
            "trace": result["trace"],
            "agent": agent_name,
            "usage": sum_usage(state.get("usage", {}), result.get("usage", {})),
            "cached": result.get("cached", False),
        }

    return node


def escalate_node(state: SupportState) -> dict:
    result = escalate_to_human(
        reason="Could not classify or resolve the request automatically",
        context=state["user_message"],
    )
    return {
        "reply": result["message"],
        "trace": [{"agent": "escalate", "tool": "escalate_to_human", "args": {}, "result": result}],
        "agent": "escalate",
        "usage": state.get("usage", {}),
    }


def build_graph():
    graph = StateGraph(SupportState)
    graph.add_node("route", route_node)
    graph.add_node("order", _make_agent_node("order", run_order_agent))
    graph.add_node("refund", _make_agent_node("refund", run_refund_agent))
    graph.add_node("payment", _make_agent_node("payment", run_payment_agent))
    graph.add_node("faq", _make_agent_node("faq", run_faq_agent))
    graph.add_node("escalate", escalate_node)

    graph.add_edge(START, "route")
    graph.add_conditional_edges(
        "route",
        lambda state: state["route"],
        {"ORDER": "order", "REFUND": "refund", "PAYMENT": "payment", "FAQ": "faq", "ESCALATE": "escalate"},
    )
    for node in ("order", "refund", "payment", "faq", "escalate"):
        graph.add_edge(node, END)

    return graph.compile()


_GRAPH = build_graph()


def run_orchestrator(user_message: str, history: list | None = None) -> dict:
    result, escalation = call_with_retry(
        lambda: _GRAPH.invoke({"user_message": user_message, "history": history or [], "trace": []}),
        escalate_reason="Agent pipeline failed (e.g. rate limit or API error)",
        escalate_context=user_message,
    )
    if escalation is not None:
        result = {
            "reply": escalation["message"],
            "trace": [{"agent": "escalate", "tool": "escalate_to_human", "args": {}, "result": escalation}],
            "agent": "escalate",
            "route": "ESCALATE",
            "usage": {},
        }

    logger.info(
        "agent_decision",
        extra={
            "extra_fields": {
                "user_message": user_message,
                "route": result.get("route"),
                "agent": result.get("agent"),
                "tools_called": [t["tool"] for t in result.get("trace", [])],
                "usage": result.get("usage"),
            }
        },
    )
    return result
