"""Registry of every publicly available *free* LLM provider and model.

Sources: each provider's free-tier API docs (as of 2026).  Model ids marked
``:free`` on OpenRouter, the ``-free`` suffixes on Groq/OpenRouter-compatible
endpoints, and Gemini's free ``generativelanguage`` tier are included.

Each provider entry declares:
  - ``kind``: wire protocol ("openai", "gemini", "hf_inference")
  - ``base_url`` / ``url``
  - ``key_env``: environment variable holding the (free) API key
  - ``signup``: where to obtain a free key
  - ``models``: list of free model ids
  - ``headers_extra``: optional static headers
"""

from typing import Any

OPENROUTER_MODELS: list[str] = [
    # Popular `:free` models on OpenRouter (no credit card required).
    "meta-llama/llama-3.1-8b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "google/gemma-3-27b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
    "qwen/qwen3-30b-a3b:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "deepseek/deepseek-r1:free",
    "deepseek/deepseek-r1-0528:free",
    "microsoft/wizardlm-2-8x22b:free",
    "gryphe/mythomax-l2-13b:free",
    "ai21/jamba-large-1.7:free",
    "cognitivecomputations/dolphin-mixtral-8x22b:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "teknium/openhermes-2.5-mistral-7b:free",
    "x-ai/grok-3-mini:free",
    "zerogpt/gptzero-m:free",
    "agentica-org/deepcoder-14b-preview:free",
    "aaron-lb/sus-instruct:free",
    "huggingfaceh4/zephyr-7b-beta:free",
    "alpindale/magnum-72b:free",
    "gmxside/mmra1-3b-rl-v2:free",
    "nvidia/llama-3.1-nemotron-70b-instruct:free",
    "openchat/openchat-7b:free",
    "undi95/toppy-m-7b:free",
    "arcee-ai/spotlight:free",
    "cohere/north-mini-code:free",
    "lyno/abstract-nlp-7b:free",
    "google/gemma-3n-e4b-it:free",
    "allenai/olmo-2-0312-32b-instruct:free",
    "liquid/lfm-7b:free",
    "arctic-arxiv/arctic-instruct:free",
    "dria/supernova-mlv3-32b-bf16:free",
    "sao10k/l3-lunaris-8b:free",
    "sophosympatheia/midnight-rose-70b:free",
    "mythologic/mistgen-7b:free",
    "gryphe/mythomist-7b:free",
    "inflection/inflection-3-pi:free",
    "inflection/inflection-3-productivity:free",
    "upstage/solar-pro-preview-instruct:free",
    "cohere/command-r7b-12-2024:free",
    "cohere/command-r-08-2024:free",
    "cohere/command-r-plus-08-2024:free",
    "tngtech/deepseek-r1t2-chimera:free",
    "tngtech/tng deepseek-r1t-chimera:free",
    "openrouter/auto:free",
]

GROQ_MODELS: list[str] = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "gemma2-9b-it",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "qwen-qwq-32b",
    "deepseek-r1-distill-llama-70b",
    "moonshotai/kimi-k2-instruct",
]

GEMINI_MODELS: list[str] = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

HUGGINGFACE_MODELS: list[str] = [
    "mistralai/Mistral-7B-Instruct-v0.3",
    "google/gemma-2-9b-it",
    "Qwen/Qwen2.5-7B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
]

COHERE_MODELS: list[str] = ["command-r7b-12-2024", "c4ai-aya-expanse-8b"]

MISTRAL_MODELS: list[str] = [
    "mistral-small-latest",
    "open-mistral-nemo",
    "mistral-tiny-latest",
    "pixtral-12b-2409",
]

GH_MODELS: list[str] = [
    "Meta-Llama-3.1-8B-Instruct",
    "Meta-Llama-3.1-70B-Instruct",
    "Phi-3.5-mini-instruct",
    "Phi-4",
    "Mistral-large-2407",
    "Mistral-3",
    "o1-mini",
    "CoHere-rerank",
]

DEEPSEEK_MODELS: list[str] = ["deepseek-chat", "deepseek-reasoner"]

TOGETHER_MODELS: list[str] = [
    "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    "Qwen/Qwen2.5-7B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
]

FIREWORKS_MODELS: list[str] = [
    "accounts/fireworks/models/llama-v3p1-8b-instruct",
    "accounts/fireworks/models/qwen2p5-7b-instruct",
    "accounts/fireworks/models/firefunction-v2",
]

CLOUDFLARE_MODELS: list[str] = [
    "@cf/meta/llama-3.1-8b-instruct",
    "@cf/meta/llama-3.3-70b-instruct",
    "@cf/mistral/mistral-7b-instruct-v0.1",
    "@cf/qwen/qwen1.5-14b-chat-awq",
    "@cf/google/gemma-3-12b-it",
    "@cf/deepseek/deepseek-r1-distill-qwen-32b",
    "@cf/the-eye/beacon-llama-3.3-70b-instruct-ep1-1",
    "@cf/meta/llama-4-scout-17b-16e-instruct",
]

GROQ_OPENAI_COMPAT_NOTE = "Groq also exposes llama-guard, whisper-large-v3 (free STT) etc."

WANDB_MODELS: list[str] = [
    "gpt-oss-20b",
    "gpt-oss-120b",
    "qwen2.5-7b-instruct",
    "llama-3.1-8b-instruct",
]

PERPLEXITY_MODELS: list[str] = [
    "perplexity-ai/r1-1776",  # free via OpenRouter & Together; listed for reference
]

# No-key-required endpoints (truly zero-config free tiers):
JOHNNYBOT_MODELS: list[str] = [
    "gpt-4o-mini",
    "gpt-4o",
    "claude-3-5-sonnet-20241022",
    "gemini-2.0-flash",
    "deepseek-chat",
    "grok-3",
]

OLLAMA_MODELS: list[str] = [
    "llama3.1:8b",
    "llama3.2:3b",
    "qwen2.5:7b",
    "mistral:7b",
    "gemma2:9b",
    "deepseek-r1:8b",
    "phi4:latest",
]

PROVIDERS: dict[str, dict[str, Any]] = {
    "openrouter": {
        "kind": "openai",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key_env": "OPENROUTER_API_KEY",
        "signup": "https://openrouter.ai/keys",
        "note": "Free tier: many `:free` models, no credit card required.",
        "models": OPENROUTER_MODELS,
        "headers_extra": {
            "HTTP-Referer": "https://cue-agent.example.com",
            "X-Title": "Cue Agent System",
        },
    },
    "groq": {
        "kind": "openai",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "signup": "https://console.groq.com/keys",
        "note": "Free tier with generous rate limits, very fast inference.",
        "models": GROQ_MODELS,
    },
    "gemini": {
        "kind": "gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/models",
        "key_env": "GEMINI_API_KEY",
        "signup": "https://aistudio.google.com/app/apikey",
        "note": "Google AI Studio free tier (RPM/RPD limits).",
        "models": GEMINI_MODELS,
    },
    "huggingface": {
        "kind": "hf_inference",
        "base_url": "https://api-inference.huggingface.co/models",
        "key_env": "HUGGINGFACE_API_KEY",
        "signup": "https://huggingface.co/settings/tokens",
        "note": "Free serverless inference tier (rate limited, cold starts).",
        "models": HUGGINGFACE_MODELS,
    },
    "cohere": {
        "kind": "openai",
        "url": "https://api.cohere.com/v2/chat",
        "key_env": "COHERE_API_KEY",
        "signup": "https://dashboard.cohere.com/api-keys",
        "note": "Free trial tier (Developer plan).",
        "models": COHERE_MODELS,
    },
    "mistral": {
        "kind": "openai",
        "url": "https://api.mistral.ai/v1/chat/completions",
        "key_env": "MISTRAL_API_KEY",
        "signup": "https://console.mistral.ai/api-keys",
        "note": "Free experiment tier (La Plateforme, rate limited).",
        "models": MISTRAL_MODELS,
    },
    "github": {
        "kind": "openai",
        "url": "https://models.inference.ai.azure.com/chat/completions",
        "key_env": "GITHUB_TOKEN",
        "signup": "https://github.com/settings/tokens",
        "note": "GitHub Models free tier with a GitHub account token.",
        "models": GH_MODELS,
    },
    "deepseek": {
        "kind": "openai",
        "url": "https://api.deepseek.com/chat/completions",
        "key_env": "DEEPSEEK_API_KEY",
        "signup": "https://platform.deepseek.com/api_keys",
        "note": "Very cheap; free promo windows occur regularly.",
        "models": DEEPSEEK_MODELS,
    },
    "together": {
        "kind": "openai",
        "url": "https://api.together.xyz/v1/chat/completions",
        "key_env": "TOGETHER_API_KEY",
        "signup": "https://api.together.xyz/settings/api-keys",
        "note": "Free credits on signup plus `-Free` models.",
        "models": TOGETHER_MODELS,
    },
    "fireworks": {
        "kind": "openai",
        "url": "https://api.fireworks.ai/inference/v1/chat/completions",
        "key_env": "FIREWORKS_API_KEY",
        "signup": "https://app.fireworks.ai/settings/users/api-keys",
        "note": "Free credits on signup; serverless playground is free.",
        "models": FIREWORKS_MODELS,
    },
    "cloudflare": {
        # Workers AI REST API: OpenAI-compatible /v1/chat/completions path.
        "kind": "openai",
        "url": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions",
        "key_env": "CLOUDFLARE_API_TOKEN",
        "account_env": "CLOUDFLARE_ACCOUNT_ID",
        "signup": "https://dash.cloudflare.com/?to=/:account/ai/workers-ai",
        "note": "Workers AI free tier (10k neurons/day); needs account id + token.",
        "models": CLOUDFLARE_MODELS,
    },
    "ollama": {
        # Local/self-hosted Ollama server — completely free, no key required.
        "kind": "openai",
        "url": "http://localhost:11434/v1/chat/completions",
        "key_env": "OLLAMA_API_KEY",  # optional; any value works locally
        "no_key_required": True,
        "signup": "https://ollama.com/download",
        "note": "Local free models via Ollama (no cloud key needed).",
        "models": OLLAMA_MODELS,
    },
    "wandb": {
        "kind": "openai",
        "url": "https://api.wandb.ai/llm/v1/chat/completions",
        "key_env": "WANDB_API_KEY",
        "signup": "https://wandb.ai/settings",
        "note": "Weights & Biases inference free tier (gpt-oss etc.).",
        "models": WANDB_MODELS,
    },
    "johnnybot": {
        # Aggregator that proxies several frontier models with no key at all.
        "kind": "openai",
        "url": "https://api.johnnybot.com/api/join-chat",
        "key_env": "JOHNNYBOT_API_KEY",
        "no_key_required": True,
        "signup": "https://johnnybot.com",
        "note": "Zero-config free proxy tier (unreliable; last-resort fallback).",
        "models": JOHNNYBOT_MODELS,
    },
}


def provider_config(name: str) -> dict[str, Any]:
    try:
        return PROVIDERS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown provider: {name}") from exc
