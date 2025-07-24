"""
Summarization processor implementation.
"""

import logging
from typing import Any

from ..common.job import JobProcessor
from ..common.models import JobType
from .model import summarize_with_model

# Logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("summarization")


class SummarizationProcessor(JobProcessor):
    """Summarization processor implementation."""

    def __init__(self, job_type: JobType, request_id: str, **kwargs):
        """
        Initialize summarization processor.

        Args:
            job_type: Type of job
            request_id: Request ID
            **kwargs: Additional parameters
        """
        super().__init__(job_type, request_id, **kwargs)

    def validate_input(self, text: str, strength: int) -> None:  # type: ignore
        """
        Validate input parameters.

        Args:
            text: Text to summarize
            strength: Summarization strength (1-5)

        Raises:
            ValueError: If text or strength is invalid
        """
        # Check if text is valid
        if not text or not isinstance(text, str):
            raise ValueError("Invalid text input")

        # Check if strength is valid
        if not isinstance(strength, int) or strength < 1 or strength > 5:
            raise ValueError("Invalid strength value (must be 1-5)")

    def execute(self, text: str, strength: int) -> dict[str, Any]:  # type: ignore
        """
        Execute summarization processing.

        Args:
            text: Text to summarize
            strength: Summarization strength (1-5)

        Returns:
            Dictionary containing the summarization result
        """
        # Perform summarization
        summarize_result = summarize_with_model(text, strength)

        # Return result
        return {
            "summary": summarize_result["summary"],
            "stats": summarize_result["stats"],
        }
