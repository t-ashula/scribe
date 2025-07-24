"""
Common data models for the Scribe package.
"""

from enum import Enum

from pydantic import BaseModel, Field


class JobType(str, Enum):
    """Job type enum."""

    TRANSCRIPTION = "transcription"
    SUMMARIZATION = "summarization"


class JobStatus(str, Enum):
    """Job status enum."""

    PENDING = "pending"
    WORKING = "working"
    DONE = "done"
    ERROR = "error"


class JobRequest(BaseModel):
    """Base job request model."""

    job_type: JobType


class JobResponse(BaseModel):
    """Base job response model."""

    request_id: str


class JobStatusResponse(BaseModel):
    """Base job status response model."""

    status: JobStatus
    error: str | None = None
    expires_at: str | None = None


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str


class TranscriptionRequest(JobRequest):
    """Transcription request model."""

    job_type: JobType = JobType.TRANSCRIPTION
    language: str = "ja"
    model: str = "base"


class TranscriptionStatusResponse(JobStatusResponse):
    """Transcription status response model."""

    text: str | None = None


class SummarizationRequest(JobRequest):
    """Summarization request model."""

    job_type: JobType = JobType.SUMMARIZATION
    text: str
    strength: int = Field(..., ge=1, le=5, description="Summarization strength (1-5)")


class SummarizationStatusResponse(JobStatusResponse):
    """Summarization status response model."""

    summary: str | None = None
