import hashlib
import math
import os
import re
from functools import lru_cache
from typing import List, Optional

from utils.llm_client import call_llm
from utils.logger import api_logger


TOKEN_RE = re.compile(r"[a-z0-9']+")


def get_embedding_provider() -> str:
    provider = os.getenv("EMBEDDING_PROVIDER")
    if provider:
        return provider.lower()
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("VOYAGE_API_KEY"):
        return "voyage"
    return "local_hash"


@lru_cache(maxsize=1)
def _openai_client():
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install the openai package to use EMBEDDING_PROVIDER=openai") from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
    return OpenAI(api_key=api_key)


@lru_cache(maxsize=1)
def _voyage_client():
    try:
        import voyageai
    except ImportError as exc:
        raise RuntimeError("Install the voyageai package to use EMBEDDING_PROVIDER=voyage") from exc

    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        raise RuntimeError("VOYAGE_API_KEY is required when EMBEDDING_PROVIDER=voyage")
    return voyageai.Client(api_key=api_key)


def _normalise(vector: List[float]) -> List[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _local_hash_embedding(text: str) -> List[float]:
    dim = int(os.getenv("LOCAL_EMBEDDING_DIM", "384"))
    vector = [0.0] * dim
    tokens = TOKEN_RE.findall(text.lower())

    features = list(tokens)
    features.extend(f"{left} {right}" for left, right in zip(tokens, tokens[1:]))

    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[bucket] += sign

    return _normalise(vector)


def get_embedding(text: str, model: Optional[str] = None) -> List[float]:
    """
    Get an embedding vector for text.

    Providers:
    - openai: requires OPENAI_API_KEY
    - voyage: requires VOYAGE_API_KEY
    - local_hash: no API key, keyword-style retrieval fallback
    """
    provider = get_embedding_provider()
    api_logger.debug(
        f"Generating embedding - Provider: {provider}, Text length: {len(text)} chars"
    )

    if provider == "openai":
        model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        response = _openai_client().embeddings.create(input=text, model=model)
        usage = response.usage
        api_logger.debug(f"Embedding generated | Provider: openai | Tokens: {usage.total_tokens}")
        return response.data[0].embedding

    if provider == "voyage":
        model = model or os.getenv("EMBEDDING_MODEL", "voyage-3.5")
        response = _voyage_client().embed([text], model=model)
        api_logger.debug(f"Embedding generated | Provider: voyage | Model: {model}")
        return response.embeddings[0]

    if provider == "local_hash":
        vector = _local_hash_embedding(text)
        api_logger.debug(
            f"Embedding generated | Provider: local_hash | Dimension: {len(vector)}"
        )
        return vector

    raise RuntimeError(f"Unsupported EMBEDDING_PROVIDER: {provider}")


def call_openai(prompt: str, model: Optional[str] = None):
    """
    Backward-compatible wrapper for older agents.
    Uses the configured LLM provider, not only OpenAI.
    """
    return call_llm([{"role": "user", "content": prompt}], model=model)
