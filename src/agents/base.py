from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.llm import extract_usage, get_llm

_EMPTY_USAGE = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def as_text(content) -> str:
    """Gemini sometimes returns content as a list of typed blocks instead of a plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


def sum_usage(*usages: dict) -> dict:
    total = dict(_EMPTY_USAGE)
    for usage in usages:
        for key in total:
            total[key] += (usage or {}).get(key) or 0
    return total


def run_tool_agent(
    agent_name: str,
    system_prompt: str,
    agent_tools: list,
    user_message: str,
    history: list | None = None,
    max_rounds: int = 4,
) -> dict:
    """Generic tool-calling loop shared by every specialist agent."""
    tools_by_name = {t.name: t for t in agent_tools}
    llm = get_llm().bind_tools(agent_tools)

    messages: list = [SystemMessage(content=system_prompt)]
    messages += history or []
    messages.append(HumanMessage(content=user_message))

    trace = []
    usage = dict(_EMPTY_USAGE)

    ai_msg: AIMessage = llm.invoke(messages)
    usage = sum_usage(usage, extract_usage(ai_msg))
    messages.append(ai_msg)

    rounds = 0
    while ai_msg.tool_calls and rounds < max_rounds:
        for call in ai_msg.tool_calls:
            tool_fn = tools_by_name[call["name"]]
            result = tool_fn.invoke(call["args"])
            trace.append({"agent": agent_name, "tool": call["name"], "args": call["args"], "result": result})
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
        ai_msg = llm.invoke(messages)
        usage = sum_usage(usage, extract_usage(ai_msg))
        messages.append(ai_msg)
        rounds += 1

    return {
        "reply": as_text(ai_msg.content),
        "trace": trace,
        "messages": messages,
        "agent": agent_name,
        "usage": usage,
    }
