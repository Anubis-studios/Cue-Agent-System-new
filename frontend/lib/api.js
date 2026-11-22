export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.BACKEND_HOST ? `https://${process.env.BACKEND_HOST}` : "") ||
  "http://localhost:8000";

export async function fetchWithRetry(url, options = {}, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url, options);
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
      return res;
    } catch (err) { if (i === retries - 1) throw err; await new Promise(r => setTimeout(r, 1000 * (i + 1))); }
  }
}
