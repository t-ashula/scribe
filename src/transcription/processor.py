"""
Transcription processor implementation.
"""

import logging
import os
from pathlib import Path
from typing import Any

from ..common.job import JobProcessor
from ..common.models import JobType
from .model import transcribe_with_model

# Logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("transcription")

# Upload directory
UPLOAD_DIR = Path(os.getenv("GESHI_UPLOAD_DIR", "tmp/uploads"))
UPLOAD_DIR.mkdir(exist_ok=True, parents=True)


class TranscriptionProcessor(JobProcessor):
    """Transcription processor implementation."""

    def __init__(self, job_type: JobType, request_id: str, **kwargs):
        """
        Initialize transcription processor.

        Args:
            job_type: Type of job
            request_id: Request ID
            **kwargs: Additional parameters
        """
        super().__init__(job_type, request_id, **kwargs)

    def validate_input(self, file_path: str, language: str, model: str) -> None:  # type: ignore
        """
        Validate input parameters.

        Args:
            file_path: Path to the audio file
            language: Language code (e.g., ja)
            model: Model name to use (e.g., base)

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If language or model is invalid
        """
        # Check if file exists
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Validate language
        valid_languages = ["ja", "en"]
        if language not in valid_languages:
            raise ValueError(f"Invalid language code: {language}")

    def execute(self, file_path: str, language: str, model: str) -> dict[str, Any]:  # type: ignore
        """
        Execute transcription processing.

        Args:
            file_path: Path to the audio file
            language: Language code (e.g., ja)
            model: Model name to use (e.g., base)

        Returns:
            Dictionary containing the transcription result
        """
        # Perform transcription
        transcribe_result = transcribe_with_model(file_path, language)

        # Return result
        return {
            "text": transcribe_result["text"],
            "segments": transcribe_result["segments"],
            "stats": transcribe_result["stats"],
        }
