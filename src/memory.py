from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, HumanMessage


@dataclass
class ConversationMemory:
    """Cross-turn conversation state: plain text history (safe to hand to any
    specialist agent, regardless of which agent handled earlier turns) plus a
    remembered 'last order discussed' so the customer doesn't need to repeat it."""

    turns: list = field(default_factory=list)
    last_order_id: int | None = None

    def add_turn(self, user_message: str, reply: str) -> None:
        self.turns.append(HumanMessage(content=user_message))
        self.turns.append(AIMessage(content=reply))

    def update_last_order_id(self, trace: list) -> None:
        for entry in trace:
            args = entry.get("args") or {}
            result = entry.get("result") or {}
            order_id = args.get("order_id")
            if order_id is None and isinstance(result, dict):
                order_id = result.get("order_id")
            if order_id is not None:
                self.last_order_id = order_id

    def context_note(self) -> str:
        if self.last_order_id is not None:
            return f"(Context: the customer was last discussing order {self.last_order_id}.)\n"
        return ""
