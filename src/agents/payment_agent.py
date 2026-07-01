from langchain_core.tools import tool

from src import tools as backend_tools
from src.agents.base import run_tool_agent


@tool
def get_payment_status(order_id: int) -> dict:
    """Look up the payment status (pending/paid/refunded) for an order."""
    return backend_tools.get_payment_status(order_id)


@tool
def process_payment(order_id: int, method: str) -> dict:
    """Process a pending payment for an order using the given method (e.g. 'card', 'paypal')."""
    return backend_tools.process_payment(order_id, method)


PAYMENT_TOOLS = [get_payment_status, process_payment]

SYSTEM_PROMPT = (
    "You are the Payment Agent for an e-commerce support system. "
    "You can check payment status and process a pending payment. "
    "Only process a payment that is currently pending; if it's already paid or refunded, explain that instead. "
    "Always call a tool to get real data before answering; never guess. "
    "Reply concisely and naturally to the customer."
)


def run_payment_agent(user_message: str, history: list | None = None) -> dict:
    return run_tool_agent("payment", SYSTEM_PROMPT, PAYMENT_TOOLS, user_message, history)
