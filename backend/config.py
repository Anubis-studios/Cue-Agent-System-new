"""Centralised application configuration read from environment variables."""

import os


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


# Database
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "cue.db")

# LLM providers
LLM_TIMEOUT_SECONDS: int = _int_env("LLM_TIMEOUT_SECONDS", 30)
LLM_MAX_RETRIES: int = _int_env("LLM_MAX_RETRIES", 2)
LLM_FALLBACK_CHAIN: list[str] = [
    p.strip()
    for p in os.getenv(
        "LLM_FALLBACK_CHAIN",
        "openrouter,groq,gemini,huggingface,cohere,mistral,github,"
        "together,fireworks,cloudflare,wandb,deepseek,ollama,johnnybot",
    ).split(",")
    if p.strip()
]
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# Response cache
CACHE_TTL_SECONDS: int = _int_env("CACHE_TTL_SECONDS", 300)

# API server
ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

# Workers
WORKER_POLL_INTERVAL_SECONDS: int = _int_env("WORKER_POLL_INTERVAL", 10)

# Vector memories (optional ChromaDB semantic recall)
VECTOR_MEMORY_ENABLED: bool = os.getenv("VECTOR_MEMORY", "0") == "1"
CHROMA_DIR: str = os.getenv("CHROMA_DIR", ".chroma")

# Agent skills
SKILLS_DIR: str = os.getenv("SKILLS_DIR", "")  # optional user skill directory

# MCP servers (JSON: {"name": {"command": "..."} or {"url": "..."}})
MCP_SERVERS_RAW: str = os.getenv("MCP_SERVERS", "")
