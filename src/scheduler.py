"""
RQ scheduler implementation for the Scribe package.
"""

import logging
import os
import shutil
import sys
from pathlib import Path

import redis
from rq_scheduler import Scheduler  # type: ignore

# Logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("scheduler")

# Redis connection settings
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Upload directory
UPLOAD_DIR = Path(os.getenv("GESHI_UPLOAD_DIR", "tmp/uploads"))


# Cleanup job for transcription uploads
def cleanup_transcription_uploads():
    """Clean up unused upload directories."""
    logger.info("Starting transcription uploads cleanup job")

    # Exit if uploads directory doesn't exist
    if not UPLOAD_DIR.exists():
        logger.info("Upload directory does not exist")
        return

    # Connect to Redis
    conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

    # Check files in uploads directory
    for item in UPLOAD_DIR.iterdir():
        if item.is_dir():
            request_id = item.name
            # Delete if key doesn't exist in Redis
            if not conn.exists(f"transcription:{request_id}"):
                logger.info(f"Deleting unnecessary directory: {request_id}")
                try:
                    shutil.rmtree(item)
                except Exception as e:
                    logger.error(f"Failed to delete directory: {e}")

    logger.info("Transcription uploads cleanup job completed")


# Cleanup job for expired Redis keys
def cleanup_expired_keys():
    """Clean up expired Redis keys."""
    logger.info("Starting expired keys cleanup job")

    # This is handled automatically by Redis TTL, but we can add additional
    # cleanup logic here if needed

    logger.info("Expired keys cleanup job completed")


def start_scheduler():
    """Start RQ scheduler."""
    try:
        # Connect to Redis
        conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

        # Initialize scheduler
        scheduler = Scheduler(connection=conn)

        # Clear existing jobs
        for job in scheduler.get_jobs():
            scheduler.cancel(job)

        # Schedule cleanup jobs

        # Run daily at midnight
        scheduler.cron(
            "0 0 * * *",
            func=cleanup_transcription_uploads,
            id="cleanup_transcription_uploads",
        )

        # Run weekly on Sunday at 1 AM
        scheduler.cron(
            "0 1 * * 0", func=cleanup_expired_keys, id="cleanup_expired_keys"
        )

        logger.info("Scheduler started")

        # Run scheduler
        scheduler.run()
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    start_scheduler()
