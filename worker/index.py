"""Vercel Serverless Function entry point for the worker service.

Invoked on a schedule by Vercel Crons (see ``crons`` in vercel.json) or via
POST to its URL. Each invocation drains currently pending jobs from the
database and returns promptly — long-lived polling belongs on Render/other
persistent hosts (see render.yaml), while cron-driven draining fits Vercel's
stateless model.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from backend.db.database import enqueue_job, get_pending_jobs, init_db, update_job_status
from backend.workers.video_worker import process_video_job

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cue-worker")

MAX_JOBS_PER_TICK = 10


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from backend.db.database import db_backend

    logger.info("Worker DB ready (%s)", db_backend())
    yield


app = FastAPI(title="Cue Worker Service", version="1.2.0", lifespan=lifespan)


class JobIn(BaseModel):
    job_type: str = "video_processing"
    payload: dict = {}


@app.get("/")
def root() -> dict:
    return {"service": "cue-worker", "mode": "serverless-cron"}


@app.post("/jobs")
def create_job(job: JobIn) -> dict:
    """Optionally enqueue work directly against the worker service."""
    job_id = enqueue_job(job.job_type, job.payload)
    return {"success": True, "job_id": job_id}


def _drain() -> dict:
    init_db()
    processed = []
    for kind in ("video_processing", None):
        jobs = get_pending_jobs(job_type=kind)[:MAX_JOBS_PER_TICK]
        for j in jobs:
            if j["id"] in processed:
                continue
            try:
                process_video_job(j["id"], j["payload"])
            except Exception as exc:
                logger.error("Job %s failed: %s", j["id"], exc)
                update_job_status(j["id"], "failed", error=str(exc))
            processed.append(j["id"])
        if kind is None:
            break
    return {"processed": processed, "count": len(set(processed))}


@app.get("/cron/worker-tick")
@app.get("/tick")
def tick_get() -> dict:
    """Target for Vercel Cron GET requests."""
    return _drain()


@app.post("/cron/worker-tick")
@app.post("/tick")
def tick_post() -> dict:
    return _drain()
