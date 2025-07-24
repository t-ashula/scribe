"""
Job registry for the Scribe package.
"""

from typing import Any

import ulid
from rq import Queue

from .job import JobProcessor
from .models import JobType
from .redis_client import RedisClient
from .status import StatusManager


class JobRegistry:
    """Job registry for managing job processors."""

    def __init__(self):
        """Initialize job registry."""
        self.redis_client = RedisClient()
        self.status_manager = StatusManager(self.redis_client)
        self.queue = Queue(connection=self.redis_client.conn)
        self.processors: dict[JobType, type[JobProcessor]] = {}

    def register_processor(
        self, job_type: JobType, processor_class: type[JobProcessor]
    ) -> None:
        """
        Register processor class for job type.

        Args:
            job_type: Type of job
            processor_class: Processor class for the job type
        """
        self.processors[job_type] = processor_class

    def enqueue_job(self, job_type: JobType, **kwargs) -> str:
        """
        Enqueue job for processing.

        Args:
            job_type: Type of job
            **kwargs: Job-specific parameters

        Returns:
            Request ID

        Raises:
            ValueError: If no processor is registered for the job type
        """
        # Generate request ID
        request_id = str(ulid.ULID())

        # Save initial status
        self.status_manager.set_pending(job_type.value, request_id)

        # Get processor class
        processor_class = self.processors.get(job_type)
        if not processor_class:
            raise ValueError(f"No processor registered for job type: {job_type}")

        # Create processor instance
        processor = processor_class(job_type, request_id)

        # Enqueue job
        self.queue.enqueue(processor.process, **kwargs)

        return request_id

    def get_job_status(self, job_type: JobType, request_id: str) -> dict[str, Any]:
        """
        Get job status.

        Args:
            job_type: Type of job
            request_id: Request ID

        Returns:
            Dictionary containing job status and data
        """
        return self.status_manager.get_status(job_type.value, request_id)
