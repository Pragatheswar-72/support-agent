import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# Sticky index into the model pool, shared across all get_llm() calls in this
# process so a working model keeps getting used instead of re-trying exhausted
# ones from the start every turn.
_rotation_state = {"index": 0}


def _load_gemini_keys() -> list[str]:
    multi = os.environ.get("GEMINI_API_KEYS")
    if multi:
        keys = [k.strip() for k in multi.split(",") if k.strip()]
        if keys:
            return keys
    single = os.environ.get("GEMINI_API_KEY")
    if single:
        return [single]
    return []


def _is_quota_error(exc: Exception) -> bool:
    text = str(exc)
    return "RESOURCE_EXHAUSTED" in text or "429" in text


class RotatingChatModel:
    """Wraps multiple chat model clients (across API keys and/or providers)
    and rotates to the next one when the current one hits a quota/rate-limit error."""

    def __init__(self, models: list, state: dict):
        self._models = models
        self._state = state

    def bind_tools(self, tools):
        return RotatingChatModel([m.bind_tools(tools) for m in self._models], state=self._state)

    def invoke(self, messages):
        n = len(self._models)
        last_exc: Exception | None = None
        for offset in range(n):
            idx = (self._state["index"] + offset) % n
            try:
                result = self._models[idx].invoke(messages)
                self._state["index"] = idx
                return result
            except Exception as exc:  # noqa: BLE001 - re-raised below if not a quota error
                last_exc = exc
                if not _is_quota_error(exc):
                    raise
        raise last_exc


def get_llm(model: str | None = None, temperature: float = 0.0) -> RotatingChatModel:
    model_name = model or DEFAULT_MODEL
    models = [
        ChatGoogleGenerativeAI(model=model_name, google_api_key=key, temperature=temperature, max_retries=0)
        for key in _load_gemini_keys()
    ]

    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        from langchain_groq import ChatGroq

        models.append(ChatGroq(model=GROQ_MODEL, api_key=groq_key, temperature=temperature, max_retries=0))

    if not models:
        raise RuntimeError("No LLM configured. Set GEMINI_API_KEY, GEMINI_API_KEYS, or GROQ_API_KEY in .env")

    return RotatingChatModel(models, state=_rotation_state)


def extract_usage(ai_message) -> dict:
    """Pull token usage out of a LangChain AIMessage, if present."""
    meta = getattr(ai_message, "usage_metadata", None)
    if not meta:
        return {}
    return {
        "input_tokens": meta.get("input_tokens"),
        "output_tokens": meta.get("output_tokens"),
        "total_tokens": meta.get("total_tokens"),
    }
