import os, sys, time, logging, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.db.database import get_pending_jobs, update_job_status

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
POLL_INTERVAL = int(os.getenv("WORKER_POLL_INTERVAL", "10"))

def process_video_job(job_id, payload):
    logger.info(f"Processing job {job_id}")
    try:
        # TODO: Implement actual video processing logic here
        result = {"status": "completed", "message": "Stub completed", "video_url": payload.get("video_url")}
        update_job_status(job_id, "completed", result=result)
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        update_job_status(job_id, "failed", error=str(e))

if __name__ == "__main__":
    logger.info("Video worker started")
    while True:
        try:
            jobs = get_pending_jobs(job_type="video_processing")
            for job in jobs:
                try: process_video_job(job["id"], job["payload"])
                except Exception as e: logger.error(f"Job {job['id']} error: {e}")
        except Exception as e: logger.error(f"Worker loop error: {e}")
        time.sleep(POLL_INTERVAL)
