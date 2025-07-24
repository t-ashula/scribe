"""
Tests for the main API server.
"""

import io
import os
import sys
from unittest import mock

import pytest
from fastapi.testclient import TestClient

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.common.models import JobType
from src.main import app

# Test client
client = TestClient(app)


# Mock setup
@pytest.fixture
def mock_job_registry():
    """Mock for JobRegistry"""
    with mock.patch("src.main.job_registry") as mock_registry:
        yield mock_registry


@pytest.fixture
def mock_ulid():
    """Mock for ulid.ULID"""
    mock_ulid_instance = mock.MagicMock()
    mock_ulid_instance.__str__.return_value = "01HPQRS9ABCDEFGHJKMNPQRST"

    mock_ulid_class = mock.MagicMock()
    mock_ulid_class.return_value = mock_ulid_instance

    with mock.patch("ulid.ULID", mock_ulid_class):
        yield mock_ulid_class


@pytest.fixture
def test_wav_file():
    """Test WAV file"""
    return io.BytesIO(b"dummy wav file content")


# Basic endpoint tests
def test_read_root():
    """Test for root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Scribe API"}


def test_health_check():
    """Test for health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# Tests for POST /transcribe endpoint
@mock.patch("src.main.magic.from_buffer")
def test_transcribe_success(
    mock_from_buffer, mock_job_registry, mock_ulid, test_wav_file
):
    """Test for successful transcription request"""
    # Prepare test file
    files = {"file": ("test.wav", test_wav_file, "audio/wav")}
    data = {"language": "ja", "model": "base"}

    # Set up mocks
    mock_job_registry.enqueue_job.return_value = "01HPQRS9ABCDEFGHJKMNPQRST"
    mock_from_buffer.return_value = "audio/x-wav"  # Mock magic to identify as WAV

    # Execute request
    response = client.post("/transcribe", files=files, data=data)

    # Verify response
    assert response.status_code == 202
    assert response.json() == {"request_id": "01HPQRS9ABCDEFGHJKMNPQRST"}

    # Verify mock calls
    mock_job_registry.enqueue_job.assert_called_once()
    mock_from_buffer.assert_called_once()  # Verify magic was called


@mock.patch("src.main.magic.from_buffer")
def test_transcribe_invalid_format(mock_from_buffer, mock_job_registry):
    """Test for invalid file format"""
    # Prepare test file (mp3 format)
    files = {"file": ("test.mp3", io.BytesIO(b"dummy mp3 content"), "audio/mp3")}
    data = {"language": "ja", "model": "base"}

    # Set up mock to identify as MP3
    mock_from_buffer.return_value = "audio/mpeg"

    # Execute request
    response = client.post("/transcribe", files=files, data=data)

    # Verify response
    assert response.status_code == 400
    assert "unsupported file format" in response.json()["detail"]["error"]

    # Verify mocks were not called
    mock_job_registry.enqueue_job.assert_not_called()
    mock_from_buffer.assert_called_once()  # Verify magic was called


# Tests for GET /transcribe/:request_id endpoint
def test_get_transcription_done(mock_job_registry):
    """Test for completed transcription status"""
    # Set up mock
    result = {
        "status": "done",
        "text": "This is a test transcription text.",
        "expires_at": "2025-04-15T00:00:00Z",
    }
    mock_job_registry.get_job_status.return_value = result

    # Execute request
    response = client.get("/transcribe/01HPQRS9ABCDEFGHJKMNPQRST")

    # Verify response
    assert response.status_code == 200
    assert response.json() == result

    # Verify mock call
    mock_job_registry.get_job_status.assert_called_once_with(
        JobType.TRANSCRIPTION, "01HPQRS9ABCDEFGHJKMNPQRST"
    )


def test_get_transcription_not_found(mock_job_registry):
    """Test for non-existent transcription result"""
    # Set up mock
    mock_job_registry.get_job_status.return_value = None

    # Execute request
    response = client.get("/transcribe/nonexistent-id")

    # Verify response
    assert response.status_code == 404
    assert "request not found" in response.json()["detail"]["error"]


# Tests for POST /summarize endpoint
def test_summarize_success(mock_job_registry, mock_ulid):
    """Test for successful summarization request"""
    # Prepare test data
    request_data = {
        "text": "This is a test text for summarization.",
        "strength": 3,
        "job_type": "summarization",
    }

    # Set up mocks
    mock_job_registry.enqueue_job.return_value = "01HPQRS9ABCDEFGHJKMNPQRST"

    # Execute request
    response = client.post("/summarize", json=request_data)

    # Verify response
    assert response.status_code == 202
    assert response.json() == {"request_id": "01HPQRS9ABCDEFGHJKMNPQRST"}

    # Verify mock calls
    mock_job_registry.enqueue_job.assert_called_once()


def test_summarize_invalid_input(mock_job_registry):
    """Test for invalid summarization input"""
    # Request with empty text
    request_data = {"text": "", "strength": 3, "job_type": "summarization"}

    # Execute request
    response = client.post("/summarize", json=request_data)

    # Verify response
    assert response.status_code == 400
    assert "error" in response.json()["detail"]

    # Verify no job was added
    mock_job_registry.enqueue_job.assert_not_called()


# Tests for GET /summarize/:request_id endpoint
def test_get_summarization_done(mock_job_registry):
    """Test for completed summarization status"""
    # Set up mock
    result = {
        "status": "done",
        "summary": "This is a test summary.",
        "expires_at": "2025-04-15T00:00:00Z",
    }
    mock_job_registry.get_job_status.return_value = result

    # Execute request
    response = client.get("/summarize/01HPQRS9ABCDEFGHJKMNPQRST")

    # Verify response
    assert response.status_code == 200
    assert response.json() == result

    # Verify mock call
    mock_job_registry.get_job_status.assert_called_once_with(
        JobType.SUMMARIZATION, "01HPQRS9ABCDEFGHJKMNPQRST"
    )


def test_get_summarization_not_found(mock_job_registry):
    """Test for non-existent summarization result"""
    # Set up mock
    mock_job_registry.get_job_status.return_value = None

    # Execute request
    response = client.get("/summarize/nonexistent-id")

    # Verify response
    assert response.status_code == 404
    assert "request not found" in response.json()["detail"]["error"]
