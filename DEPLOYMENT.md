# Deployment: Vercel app + persistent Render worker

The Vercel project serves the Next.js frontend and FastAPI API on one domain. The background video worker is a long-running Render worker defined in `render.yaml`; it polls the jobs table and must share the same PostgreSQL database as the Vercel API.

## 1. Deploy the web app to Vercel

Import this repository into Vercel and keep the project root at the repository root (`.`), so Vercel reads `vercel.json`. The rewrites send `/api/*`, `/ws/*`, `/health`, `/docs`, and `/openapi.json` to FastAPI; all other paths go to Next.js. The frontend uses same-origin API paths by default, so `NEXT_PUBLIC_API_URL` can remain unset.

## 2. Create the persistent worker and PostgreSQL on Render

Create a Render Blueprint from this repository using `render.yaml`. It defines a persistent `cue-worker` that runs `python -m backend.workers.video_worker` and a managed PostgreSQL database. The worker's `DATABASE_URL` is wired to that database by the Blueprint. The backend service in the Render Blueprint is optional if Vercel is serving the API; the Render worker and database are the components needed for background jobs.

For the Vercel API to reach the same database, copy the database provider's **external** PostgreSQL connection URL into Vercel. Do not use a private/internal Render hostname in Vercel. Keep the Render worker on its Render-provided connection string. Both URLs must point to the same database.

## 3. Set Vercel environment variables

In Vercel, open **Project → Settings → Environment Variables**. Add `DATABASE_URL` using the external Postgres connection URL, then add the provider keys you intend to use. Never commit credentials to this repository.

Supported optional provider keys (add only the providers you use):

- `OPENROUTER_API_KEY`
- `GROQ_API_KEY`
- `HUGGINGFACE_API_KEY`
- `GEMINI_API_KEY`
- `COHERE_API_KEY`
- `MISTRAL_API_KEY`
- `GITHUB_TOKEN`
- `DEEPSEEK_API_KEY`
- `TOGETHER_API_KEY`
- `FIREWORKS_API_KEY`

Optional configuration: `LLM_FALLBACK_CHAIN`, `MCP_SERVERS`, `SKILLS_DIR`, and `ALLOWED_ORIGINS`. If using browser calls on the same Vercel domain, the default local CORS origin may be changed to the deployed origin or the configured allowlist.

Set variables for Production (and Preview if previews should use the shared database/secrets), then redeploy so they are available to server functions. Configure any provider keys needed by the worker separately in Render's worker environment; Vercel environment variables are not automatically passed to Render.

## Important limits

Vercel functions are not persistent processes. Do not run the polling loop there. The Render worker is persistent, but the current `process_video_job` implementation is a stub and needs real video processing logic before it performs actual processing. PostgreSQL is durable; Vercel's local filesystem and SQLite files are not durable shared storage.
