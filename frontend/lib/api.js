const DEFAULT_API_BASE = "http://localhost:8000";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.BACKEND_HOST ? `https://${process.env.BACKEND_HOST}` : "") ||
  DEFAULT_API_BASE;

/**
 * Fetch with basic retry + linear backoff. Throws on the final failed attempt.
 */
export async function fetchWithRetry(url, options = {}, retries = 3) {
  let lastError;
  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      const res = await fetch(url, options);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      return res;
    } catch (err) {
      lastError = err;
      if (attempt < retries - 1) {
        await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
      }
    }
  }
  throw lastError;
}

/** Send a chat message and return the parsed backend response. */
export async function sendChatMessage(message, { agentId = "default", useTools = true } = {}) {
  const res = await fetchWithRetry(`${API_BASE}/api/chat/${agentId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, use_tools: useTools }),
  });
  return res.json();
}
