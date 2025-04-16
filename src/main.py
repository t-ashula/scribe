"""
Main API server for the Scribe package.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Union

import magic
import ulid
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .common.job_registry import JobRegistry
from .common.models import (
    ErrorResponse,
    JobResponse,
    JobType,
    SummarizationRequest,
    SummarizationStatusResponse,
    TranscriptionRequest,
    TranscriptionStatusResponse,
)
from .summarization.processor import SummarizationProcessor
from .transcription.processor import TranscriptionProcessor

# Application settings
UPLOAD_DIR = Path(os.getenv("GESHI_UPLOAD_DIR", "tmp/uploads"))
UPLOAD_DIR.mkdir(exist_ok=True, parents=True)
MAX_FILE_SIZE = 1 * 1024 * 1024 * 1024  # 1GiB

# Initialize job registry
job_registry = JobRegistry()
job_registry.register_processor(JobType.TRANSCRIPTION, TranscriptionProcessor)
job_registry.register_processor(JobType.SUMMARIZATION, SummarizationProcessor)

# FastAPI application
app = FastAPI(
    title="Scribe API",
    description="API for audio transcription and text summarization",
    version="0.1.0",
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Scribe API"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/transcribe", status_code=202, response_model=JobResponse)
async def transcribe_audio(
    file: UploadFile = File(...), language: str = Form("ja"), model: str = Form("base")
):
    """
    Upload an audio file for transcription.
    """
    # Check file
    if not file.filename:
        raise HTTPException(
            status_code=400, detail={"error": "unsupported file format"}
        )

    # Check file format
    mime_type = magic.from_buffer(file.file.read(1024), mime=True)
    if mime_type != "audio/x-wav":
        raise HTTPException(
            status_code=400, detail={"error": "unsupported file format"}
        )

    # Check file size (estimated from headers)
    content_length = int(file.headers.get("content-length", 0))
    if content_length > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail={"error": "file too large"})

    # Generate request ID
    request_id = str(ulid.ULID())

    # Create upload directory
    upload_path = UPLOAD_DIR / request_id
    upload_path.mkdir(exist_ok=True)

    # Save the file
    file_path = upload_path / file.filename
    with open(file_path, "wb") as buffer:
        # Reset file position
        file.file.seek(0)
        shutil.copyfileobj(file.file, buffer)

    # Enqueue job
    job_registry.enqueue_job(
        JobType.TRANSCRIPTION,
        file_path=str(file_path),
        language=language,
        model=model,
    )

    return {"request_id": request_id}


@app.get(
    "/transcribe/{request_id}",
    response_model=Union[TranscriptionStatusResponse, ErrorResponse],
    response_model_exclude_none=True,
    responses={
        200: {"model": TranscriptionStatusResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_transcription(request_id: str):
    """
    Get transcription result.
    """
    # Get result from job registry
    result = job_registry.get_job_status(JobType.TRANSCRIPTION, request_id)

    if not result:
        raise HTTPException(status_code=404, detail={"error": "request not found"})

    return result


@app.post("/summarize", status_code=202, response_model=JobResponse)
async def summarize_text(request: SummarizationRequest):
    """
    Register a job to summarize text.
    """
    if not request.text:
        raise HTTPException(status_code=400, detail={"error": "invalid input"})

    # Enqueue job
    request_id = job_registry.enqueue_job(
        JobType.SUMMARIZATION,
        text=request.text,
        strength=request.strength,
    )

    return {"request_id": request_id}


@app.get(
    "/summarize/{request_id}",
    response_model=Union[SummarizationStatusResponse, ErrorResponse],
    response_model_exclude_none=True,
    responses={
        200: {"model": SummarizationStatusResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_summarization(request_id: str):
    """
    Get summarization result.
    """
    # Get result from job registry
    result = job_registry.get_job_status(JobType.SUMMARIZATION, request_id)

    if not result:
        raise HTTPException(status_code=404, detail={"error": "request not found"})

    return result


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
