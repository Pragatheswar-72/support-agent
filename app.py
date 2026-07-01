import streamlit as st

from src.memory import ConversationMemory
from src.orchestrator import run_orchestrator

st.set_page_config(page_title="AI Customer Support Agent", page_icon="🛟", layout="wide")
st.title("🛟 AI Customer Support Agent")
st.caption("Multi-agent support system — orders, refunds, payments, FAQ")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory()
if "total_tokens" not in st.session_state:
    st.session_state.total_tokens = 0

AGENT_LABELS = {
    "order": "📦 Order",
    "refund": "💸 Refund",
    "payment": "💳 Payment",
    "faq": "❓ FAQ",
    "escalate": "🧑‍💻 Escalated to human",
}


def render_turn_meta(agent: str, trace: list, cached: bool = False) -> None:
    label = AGENT_LABELS.get(agent, agent)
    caption = f"handled by: **{label}** agent"
    if cached:
        caption += "  ·  ⚡ cached FAQ answer (no LLM call)"
    st.caption(caption)
    if trace:
        with st.expander("Agent trace"):
            st.json(trace)


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("agent"):
            render_turn_meta(message["agent"], message.get("trace", []), message.get("cached", False))

if prompt := st.chat_input("How can I help you today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    memory: ConversationMemory = st.session_state.memory
    augmented_message = memory.context_note() + prompt

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = run_orchestrator(augmented_message, history=memory.turns)
        st.markdown(result["reply"])
        render_turn_meta(result["agent"], result["trace"], result.get("cached", False))

    st.session_state.total_tokens += (result.get("usage") or {}).get("total_tokens") or 0
    memory.add_turn(prompt, result["reply"])
    memory.update_last_order_id(result["trace"])
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["reply"],
            "agent": result["agent"],
            "trace": result["trace"],
            "cached": result.get("cached", False),
        }
    )

with st.sidebar:
    st.header("Session stats")
    st.metric("Total tokens used", st.session_state.total_tokens)
    if st.session_state.memory.last_order_id:
        st.write(f"Last order discussed: **#{st.session_state.memory.last_order_id}**")
    st.divider()
    st.caption(
        "Guardrails in effect:\n"
        "- Refunds only allowed on **delivered** orders with no existing refund\n"
        "- Payments only processed while **pending**\n"
        "- Unresolvable or unclear requests are escalated to a human"
    )
