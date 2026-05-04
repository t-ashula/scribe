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


def process_job(
    job_type_value: str,
    request_id: str,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Process a queued job from plain serializable values."""
    job_type = JobType(job_type_value)
    processor_class = get_processor_class(job_type)
    processor = processor_class(job_type, request_id)
    return processor.process(**kwargs)


def get_processor_class(job_type: JobType) -> type[JobProcessor]:
    """Resolve processor class for a job type."""
    if job_type == JobType.TRANSCRIPTION:
        from ..transcription.processor import TranscriptionProcessor

        return TranscriptionProcessor

    if job_type == JobType.SUMMARIZATION:
        from ..summarization.processor import SummarizationProcessor

        return SummarizationProcessor

    raise ValueError(f"No processor registered for job type: {job_type}")


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

    def enqueue_job(
        self,
        job_type: JobType,
        request_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Enqueue job for processing.

        Args:
            job_type: Type of job
            request_id: Optional request ID supplied by caller
            **kwargs: Job-specific parameters

        Returns:
            Request ID

        Raises:
            ValueError: If no processor is registered for the job type
        """
        if request_id is None:
            request_id = str(ulid.ULID())

        self.status_manager.set_pending(job_type.value, request_id)

        processor_class = self.processors.get(job_type)
        if not processor_class:
            raise ValueError(f"No processor registered for job type: {job_type}")

        self.queue.enqueue(process_job, job_type.value, request_id, kwargs)

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
