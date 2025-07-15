"""
RQ worker implementation for the Scribe package.
"""

import logging
import os
import sys

import redis
from rq import Worker

# Logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("worker")

# Redis connection settings
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Queue names
QUEUES = ["default"]


def start_worker():
    """Start RQ worker."""
    try:
        # Connect to Redis
        redis_conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

        # Start worker
        worker = Worker(QUEUES, connection=redis_conn)
        logger.info(f"Worker started, listening on queues: {', '.join(QUEUES)}")
        worker.work()
    except Exception as e:
        logger.error(f"Worker error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    start_worker()
