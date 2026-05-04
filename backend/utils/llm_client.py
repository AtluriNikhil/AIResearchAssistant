import os
import config  # noqa: F401 - ensures project .env is loaded before provider selection
from functools import lru_cache
from typing import Any, Dict, List, Optional


Message = Dict[str, str]


def get_llm_provider() -> str:
    provider = os.getenv("LLM_PROVIDER")
    if provider:
        return provider.lower()
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "openai"


def get_default_llm_model(provider: Optional[str] = None) -> str:
    provider = provider or get_llm_provider()
    if provider == "anthropic":
        return "claude-3-5-haiku-latest"
    return "gpt-4o-mini"


@lru_cache(maxsize=1)
def _openai_client():
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install the openai package to use LLM_PROVIDER=openai") from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
    return OpenAI(api_key=api_key)


@lru_cache(maxsize=1)
def _anthropic_client():
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("Install the anthropic package to use LLM_PROVIDER=anthropic") from exc

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
    return anthropic.Anthropic(api_key=api_key)


def _extract_anthropic_text(response: Any) -> str:
    text_parts = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
    return "".join(text_parts)


def call_llm(
    messages: List[Message],
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    provider = get_llm_provider()
    model = model or os.getenv("LLM_MODEL") or get_default_llm_model(provider)
    max_tokens = max_tokens or int(os.getenv("LLM_MAX_TOKENS", "2048"))

    if provider == "anthropic":
        system_messages = [message["content"] for message in messages if message["role"] == "system"]
        chat_messages = [
            {"role": message["role"], "content": message["content"]}
            for message in messages
            if message["role"] in {"user", "assistant"}
        ]

        kwargs: Dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": chat_messages,
        }
        if system_messages:
            kwargs["system"] = "\n\n".join(system_messages)
        if temperature is not None:
            kwargs["temperature"] = temperature

        response = _anthropic_client().messages.create(**kwargs)
        return _extract_anthropic_text(response)

    if provider == "openai":
        kwargs = {
            "model": model,
            "messages": messages,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        response = _openai_client().chat.completions.create(**kwargs)
        return response.choices[0].message.content

    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")
