"""
Job processing framework for the Scribe package.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from .models import JobStatus, JobType
from .redis_client import RedisClient
from .status import StatusManager


class JobProcessor(ABC):
    """Abstract base class for job processing."""

    def __init__(
        self,
        job_type: JobType,
        request_id: str,
        redis_client: RedisClient | None = None,
    ):
        """
        Initialize job processor.

        Args:
            job_type: Type of job
            request_id: Request ID
            redis_client: Redis client instance (optional)
        """
        self.job_type = job_type
        self.request_id = request_id
        self.redis_client = redis_client or RedisClient()
        self.status_manager = StatusManager(self.redis_client)
        self.logger = logging.getLogger(f"{job_type.value}")

    def process(self, **kwargs) -> dict[str, Any]:
        """
        Process job with common workflow.

        Args:
            **kwargs: Job-specific parameters

        Returns:
            Dictionary containing the processing result
        """
        self.logger.info(f"Starting {self.job_type.value} process: {self.request_id}")

        try:
            # Update status to working
            self.status_manager.set_working(self.job_type.value, self.request_id)

            # Validate input
            self.validate_input(**kwargs)

            # Execute job-specific processing
            result = self.execute(**kwargs)

            # Save result
            self.status_manager.set_done(self.job_type.value, self.request_id, result)

            self.logger.info(
                f"{self.job_type.value} process completed: {self.request_id}"
            )
            return result

        except Exception as e:
            self.logger.error(
                f"Error occurred during {self.job_type.value} process: {e}"
            )

            # Save error information
            self.status_manager.set_error(
                self.job_type.value, self.request_id, str(e.__class__.__name__)
            )

            return {"status": JobStatus.ERROR, "error": str(e.__class__.__name__)}

    @abstractmethod
    def validate_input(self, **kwargs) -> None:
        """
        Validate input parameters.

        Args:
            **kwargs: Job-specific parameters

        Raises:
            ValueError: If input is invalid
        """
        pass

    @abstractmethod
    def execute(self, **kwargs) -> dict[str, Any]:
        """
        Execute job-specific processing.

        Args:
            **kwargs: Job-specific parameters

        Returns:
            Dictionary containing the processing result
        """
        pass
