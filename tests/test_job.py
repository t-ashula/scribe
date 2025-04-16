"""
Tests for job processing framework.
"""

import os
import sys
from unittest import mock

import pytest

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.common.job import JobProcessor
from src.common.job_registry import JobRegistry
from src.common.models import JobStatus, JobType
from src.common.redis_client import RedisClient
from src.common.status import StatusManager


# Mock job processor for testing
class MockJobProcessor(JobProcessor):
    """Mock job processor for testing."""

    def __init__(self, job_type, request_id, **kwargs):
        super().__init__(job_type, request_id, **kwargs)
        self.validate_called = False
        self.execute_called = False
        self.execute_result = {"result": "test result"}
        self.validate_error = False
        self.execute_error = False

    def validate_input(self, **kwargs):
        """Mock validate_input method."""
        self.validate_called = True
        if self.validate_error:
            raise ValueError("Validation error")

    def execute(self, **kwargs):
        """Mock execute method."""
        self.execute_called = True
        if self.execute_error:
            raise RuntimeError("Execution error")
        return self.execute_result


# Job processor tests
class TestJobProcessor:
    """Tests for JobProcessor class."""

    @pytest.fixture
    def mock_redis_client(self):
        """Mock RedisClient."""
        return mock.MagicMock(spec=RedisClient)

    @pytest.fixture
    def mock_status_manager(self):
        """Mock StatusManager."""
        return mock.MagicMock(spec=StatusManager)

    def test_process_success(self, mock_redis_client, mock_status_manager):
        """Test successful processing."""
        # Create processor with mocked dependencies
        processor = MockJobProcessor(
            JobType.TRANSCRIPTION, "test-id", redis_client=mock_redis_client
        )
        processor.status_manager = mock_status_manager

        # Call process method
        result = processor.process(param1="value1", param2="value2")

        # Verify methods were called
        assert processor.validate_called
        assert processor.execute_called

        # Verify status updates
        mock_status_manager.set_working.assert_called_once_with(
            JobType.TRANSCRIPTION.value, "test-id"
        )
        mock_status_manager.set_done.assert_called_once_with(
            JobType.TRANSCRIPTION.value, "test-id", {"result": "test result"}
        )

        # Verify result
        assert result == {"result": "test result"}

    def test_process_validation_error(self, mock_redis_client, mock_status_manager):
        """Test processing with validation error."""
        # Create processor with mocked dependencies
        processor = MockJobProcessor(
            JobType.TRANSCRIPTION, "test-id", redis_client=mock_redis_client
        )
        processor.status_manager = mock_status_manager
        processor.validate_error = True

        # Call process method
        result = processor.process(param1="value1", param2="value2")

        # Verify methods were called
        assert processor.validate_called
        assert not processor.execute_called

        # Verify status updates
        mock_status_manager.set_working.assert_called_once_with(
            JobType.TRANSCRIPTION.value, "test-id"
        )
        mock_status_manager.set_error.assert_called_once()

        # Verify result
        assert result["status"] == JobStatus.ERROR
        assert "error" in result

    def test_process_execution_error(self, mock_redis_client, mock_status_manager):
        """Test processing with execution error."""
        # Create processor with mocked dependencies
        processor = MockJobProcessor(
            JobType.TRANSCRIPTION, "test-id", redis_client=mock_redis_client
        )
        processor.status_manager = mock_status_manager
        processor.execute_error = True

        # Call process method
        result = processor.process(param1="value1", param2="value2")

        # Verify methods were called
        assert processor.validate_called
        assert processor.execute_called

        # Verify status updates
        mock_status_manager.set_working.assert_called_once_with(
            JobType.TRANSCRIPTION.value, "test-id"
        )
        mock_status_manager.set_error.assert_called_once()

        # Verify result
        assert result["status"] == JobStatus.ERROR
        assert "error" in result


# Job registry tests
class TestJobRegistry:
    """Tests for JobRegistry class."""

    @pytest.fixture
    def mock_redis_client(self):
        """Mock RedisClient."""
        mock_client = mock.MagicMock(spec=RedisClient)
        # Mock the conn attribute
        mock_client.conn = mock.MagicMock()
        return mock_client

    @pytest.fixture
    def mock_queue(self):
        """Mock RQ Queue."""
        return mock.MagicMock()

    @pytest.fixture
    def registry(self, mock_redis_client):
        """Create JobRegistry with mocked dependencies."""
        with mock.patch(
            "src.common.job_registry.RedisClient", return_value=mock_redis_client
        ):
            with mock.patch("src.common.job_registry.Queue") as mock_queue_class:
                with mock.patch(
                    "src.common.job_registry.StatusManager"
                ) as mock_status_manager:
                    mock_status_manager.return_value = mock.MagicMock()
                    mock_queue_class.return_value = mock.MagicMock()
                    registry = JobRegistry()
                    return registry

    def test_register_processor(self, registry):
        """Test registering processor class."""
        registry.register_processor(JobType.TRANSCRIPTION, MockJobProcessor)

        assert JobType.TRANSCRIPTION in registry.processors
        assert registry.processors[JobType.TRANSCRIPTION] == MockJobProcessor

    def test_enqueue_job(self, registry):
        """Test enqueueing job."""
        # Register processor
        registry.register_processor(JobType.TRANSCRIPTION, MockJobProcessor)

        # Mock ulid.ULID
        with mock.patch("ulid.ULID") as mock_ulid:
            mock_ulid_instance = mock.MagicMock()
            mock_ulid_instance.__str__.return_value = "test-id"
            mock_ulid.return_value = mock_ulid_instance

            # Call enqueue_job
            result = registry.enqueue_job(
                JobType.TRANSCRIPTION, param1="value1", param2="value2"
            )

            # Verify result
            assert result == "test-id"

            # Verify status was set to pending
            registry.status_manager.set_pending.assert_called_once_with(
                JobType.TRANSCRIPTION.value, "test-id"
            )

            # Verify job was enqueued
            registry.queue.enqueue.assert_called_once()

    def test_enqueue_job_unregistered(self, registry):
        """Test enqueueing job with unregistered processor."""
        # Don't register any processors

        # Call enqueue_job
        with pytest.raises(ValueError):
            registry.enqueue_job(
                JobType.TRANSCRIPTION, param1="value1", param2="value2"
            )

    def test_get_job_status(self, registry):
        """Test getting job status."""
        # Mock status_manager.get_status
        registry.status_manager.get_status.return_value = {
            "status": "done",
            "result": "test",
        }

        # Call get_job_status
        result = registry.get_job_status(JobType.TRANSCRIPTION, "test-id")

        # Verify result
        assert result == {"status": "done", "result": "test"}

        # Verify status_manager.get_status was called
        registry.status_manager.get_status.assert_called_once_with(
            JobType.TRANSCRIPTION.value, "test-id"
        )
