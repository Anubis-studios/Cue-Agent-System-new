import os, aiohttp, asyncio, hashlib, time
from fastapi import HTTPException
from typing import Optional

TIMEOUT = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
MAX_RETRIES = 2
CHAIN = [p.strip() for p in os.getenv("LLM_FALLBACK_CHAIN", "openrouter,groq,huggingface,gemini").split(",") if p.strip()]

_cache = {}
CACHE_TTL = 300

def _get_cache_key(prompt): return hashlib.md5(prompt.encode()).hexdigest()
def _get_from_cache(key):
    if key in _cache:
        ts, resp = _cache[key]
        if time.time() - ts < CACHE_TTL: return resp
        del _cache[key]
    return None
def _set_cache(key, resp): _cache[key] = (time.time(), resp)

async def _call_with_retry(func, prompt, max_retries=MAX_RETRIES):
    last_err = None
    for attempt in range(max_retries + 1):
        try: return await func(prompt)
        except Exception as e:
            last_err = e
            if attempt < max_retries: await asyncio.sleep(2 ** attempt)
    raise last_err

async def _call_openrouter(prompt):
    key = os.getenv("OPENROUTER_API_KEY")
    if not key: raise RuntimeError("OpenRouter key missing")
    async with aiohttp.ClientSession() as s:
        async with s.post("https://openrouter.ai/api/v1/chat/completions", 
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                          json={"model": "meta-llama/llama-3.1-8b-instruct:free", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7},
                          timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r:
            if r.status != 200: raise RuntimeError(f"OpenRouter {r.status}: {await r.text()}")
            return (await r.json())["choices"][0]["message"]["content"]

async def _call_groq(prompt):
    key = os.getenv("GROQ_API_KEY")
    if not key: raise RuntimeError("Groq key missing")
    async with aiohttp.ClientSession() as s:
        async with s.post("https://api.groq.com/openai/v1/chat/completions",
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                          json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7},
                          timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r:
            if r.status != 200: raise RuntimeError(f"Groq {r.status}: {await r.text()}")
            return (await r.json())["choices"][0]["message"]["content"]

async def _call_huggingface(prompt):
    key = os.getenv("HUGGINGFACE_API_KEY")
    if not key: raise RuntimeError("HF key missing")
    async with aiohttp.ClientSession() as s:
        async with s.post("https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3",
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                          json={"inputs": prompt}, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r:
            if r.status != 200: raise RuntimeError(f"HF {r.status}: {await r.text()}")
            data = await r.json()
            if isinstance(data, list) and len(data) > 0: return data[0]["generated_text"]
            raise RuntimeError("Unexpected HF response")

async def _call_gemini(prompt):
    key = os.getenv("GEMINI_API_KEY")
    if not key: raise RuntimeError("Gemini key missing")
    async with aiohttp.ClientSession() as s:
        async with s.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}",
                          headers={"Content-Type": "application/json"},
                          json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.7}},
                          timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r:
            if r.status != 200: raise RuntimeError(f"Gemini {r.status}: {await r.text()}")
            return (await r.json())["candidates"][0]["content"]["parts"][0]["text"]

PROVIDERS = {"openrouter": _call_openrouter, "groq": _call_groq, "huggingface": _call_huggingface, "gemini": _call_gemini}

async def generate(prompt: str) -> tuple[str, str]:
    cache_key = _get_cache_key(prompt)
    cached = _get_from_cache(cache_key)
    if cached: return cached, "cache"
    
    errors = []
    for name in CHAIN:
        if name not in PROVIDERS:
            errors.append(f"{name}: unknown"); continue
        try:
            resp = await _call_with_retry(PROVIDERS[name], prompt)
            _set_cache(cache_key, resp)
            return resp, name
        except Exception as e:
            errors.append(f"{name}: {str(e)}"); continue
    
    raise HTTPException(status_code=503, detail=f"All providers failed: {'; '.join(errors)}")
