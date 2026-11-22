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
    "meta-llama/llama-3.1-8b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "deepseek/deepseek-r1:free",
    "microsoft/wizardlm-2-8x22b:free",
    "gryphe/mythomax-l2-13b:free",
    "yi-large/yi-34b-chat:free",
    "teknium/openhermes-2.5-mistral-7b:free",
    "neversleep/llama-3.1-lumimaid-8b:free",
    "nousresearch/nous-hermes-llama2-13b:free",
]

GROQ_MODELS: list[str] = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "gemma2-9b-it",
    "meta-llama/llama-4-scout-17b-16e-instruct",
]

GEMINI_MODELS: list[str] = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

HUGGINGFACE_MODELS: list[str] = [
    "mistralai/Mistral-7B-Instruct-v0.3",
    "google/gemma-2-9b-it",
    "Qwen/Qwen2.5-7B-Instruct",
]

COHERE_MODELS: list[str] = ["command-r7b-12-2024"]

MISTRAL_MODELS: list[str] = ["mistral-small-latest", "open-mistral-nemo"]

GH_MODELS: list[str] = [
    "Meta-Llama-3.1-8B-Instruct",
    "Meta-Llama-3.1-70B-Instruct",
    "Phi-3.5-mini-instruct",
    "Mistral-large-2407",
    "CoHere-rerank",
]

WATSONX_MODELS: list[str] = [
    "meta-llama/llama-3-2-11b-vision-instruct",
    "google/gemini-2.0-flash-iter-1",
]

DEEPSEEK_MODELS: list[str] = ["deepseek-chat", "deepseek-reasoner"]

TOGETHER_MODELS: list[str] = [
    "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
]

FIREWORKS_MODELS: list[str] = [
    "accounts/fireworks/models/llama-v3p1-8b-instruct",
    "accounts/fireworks/models/qwen2p5-7b-instruct",
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
}


def provider_config(name: str) -> dict[str, Any]:
    try:
        return PROVIDERS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown provider: {name}") from exc
