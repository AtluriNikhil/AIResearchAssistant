from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env from the project root no matter where the server is started from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic" if ANTHROPIC_API_KEY else "openai")
EMBEDDING_PROVIDER = os.getenv(
    "EMBEDDING_PROVIDER",
    "openai" if OPENAI_API_KEY else "voyage" if VOYAGE_API_KEY else "local_hash",
)
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./db/faiss_index")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
