"""Background worker that polls the jobs table for video processing work."""

import logging
import time

from backend.config import WORKER_POLL_INTERVAL_SECONDS
from backend.db.database import get_pending_jobs, update_job_status

logger = logging.getLogger(__name__)


def process_video_job(job_id: int, payload: dict) -> None:
    logger.info("Processing job %s", job_id)
    try:
        # TODO: Implement actual video processing logic here.
        result = {
            "status": "completed",
            "message": "Stub completed",
            "video_url": payload.get("video_url"),
        }
        update_job_status(job_id, "completed", result=result)
    except Exception as exc:  # noqa: BLE001 - keep the worker loop alive
        logger.error("Job %s failed: %s", job_id, exc)
        update_job_status(job_id, "failed", error=str(exc))


def run(poll_interval: float = WORKER_POLL_INTERVAL_SECONDS) -> None:
    logger.info("Video worker started")
    while True:
        try:
            jobs = get_pending_jobs(job_type="video_processing")
            for job in jobs:
                process_video_job(job["id"], job["payload"])
        except Exception as exc:  # noqa: BLE001 - transient DB errors etc.
            logger.error("Worker loop error: %s", exc)
        time.sleep(poll_interval)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    run()
