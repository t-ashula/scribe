"""
Status management for the Scribe package.
"""

from datetime import datetime, timedelta
from typing import Any

from .models import JobStatus
from .redis_client import RedisClient


class StatusManager:
    """Status manager for job processing."""

    def __init__(self, redis_client: RedisClient):
        """
        Initialize status manager.

        Args:
            redis_client: Redis client instance
        """
        self.redis_client = redis_client
        self.ttl = 60 * 60 * 24  # 24 hours (seconds)

    def set_pending(self, job_type: str, job_id: str) -> None:
        """
        Set job status to pending.

        Args:
            job_type: Type of job (transcription, summarization)
            job_id: Job ID
        """
        self.redis_client.set_job_status(job_type, job_id, JobStatus.PENDING)

    def set_working(self, job_type: str, job_id: str) -> None:
        """
        Set job status to working.

        Args:
            job_type: Type of job (transcription, summarization)
            job_id: Job ID
        """
        self.redis_client.update_job_status(job_type, job_id, JobStatus.WORKING)

    def set_done(self, job_type: str, job_id: str, result: dict[str, Any]) -> None:
        """
        Set job status to done with result.

        Args:
            job_type: Type of job (transcription, summarization)
            job_id: Job ID
            result: Job result data
        """
        # Add expiration time
        expires_at = datetime.utcnow() + timedelta(seconds=self.ttl)

        # Prepare result data
        data = {
            "status": JobStatus.DONE,
            "expires_at": expires_at.isoformat() + "Z",
            **result,
        }

        # Save to Redis
        self.redis_client.set_job_status(job_type, job_id, JobStatus.DONE, data)

    def set_error(self, job_type: str, job_id: str, error: str) -> None:
        """
        Set job status to error with error message.

        Args:
            job_type: Type of job (transcription, summarization)
            job_id: Job ID
            error: Error message
        """
        data = {"status": JobStatus.ERROR, "error": error}

        self.redis_client.set_job_status(job_type, job_id, JobStatus.ERROR, data)

    def get_status(self, job_type: str, job_id: str) -> dict[str, Any] | None:
        """
        Get job status.

        Args:
            job_type: Type of job (transcription, summarization)
            job_id: Job ID

        Returns:
            Dictionary containing job status and data, or None if not found
        """
        return self.redis_client.get_job_status(job_type, job_id)
