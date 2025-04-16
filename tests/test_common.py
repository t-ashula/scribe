"""
Tests for common components.
"""

import json
import os
import sys
from unittest import mock

import pytest
import redis

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.common.job import JobProcessor
from src.common.job_registry import JobRegistry
from src.common.models import JobStatus
from src.common.redis_client import RedisClient
from src.common.status import StatusManager


# Redis client tests
class TestRedisClient:
    """Tests for RedisClient class."""

    @pytest.fixture
    def mock_redis_conn(self):
        """Mock Redis connection."""
        with mock.patch("redis.Redis") as mock_redis:
            mock_instance = mock.MagicMock()
            mock_redis.return_value = mock_instance
            yield mock_instance

    def test_init(self, mock_redis_conn):
        """Test initialization."""
        client = RedisClient()
        assert client.host == "localhost"
        assert client.port == 6379
        assert client.db == 0
        assert client.ttl == 60 * 60 * 24  # 24 hours

    def test_set_job_status(self, mock_redis_conn):
        """Test setting job status."""
        client = RedisClient()
        client.set_job_status("transcription", "test-id", "pending")

        mock_redis_conn.setex.assert_called_once_with(
            "transcription:test-id", client.ttl, json.dumps({"status": "pending"})
        )

    def test_set_job_status_with_data(self, mock_redis_conn):
        """Test setting job status with additional data."""
        client = RedisClient()
        data = {"text": "test text", "extra": "data"}
        client.set_job_status("transcription", "test-id", "done", data)

        expected_data = {"text": "test text", "extra": "data", "status": "done"}
        mock_redis_conn.setex.assert_called_once_with(
            "transcription:test-id", client.ttl, json.dumps(expected_data)
        )

    def test_get_job_status_found(self, mock_redis_conn):
        """Test getting job status when found."""
        client = RedisClient()
        mock_redis_conn.get.return_value = json.dumps(
            {"status": "done", "text": "test"}
        ).encode()

        result = client.get_job_status("transcription", "test-id")

        assert result == {"status": "done", "text": "test"}
        mock_redis_conn.get.assert_called_once_with("transcription:test-id")

    def test_get_job_status_not_found(self, mock_redis_conn):
        """Test getting job status when not found."""
        client = RedisClient()
        mock_redis_conn.get.return_value = None

        result = client.get_job_status("transcription", "test-id")

        assert result is None
        mock_redis_conn.get.assert_called_once_with("transcription:test-id")

    def test_update_job_status_existing(self, mock_redis_conn):
        """Test updating job status for existing job."""
        client = RedisClient()

        # Mock get_job_status to return existing data
        with mock.patch.object(client, "get_job_status") as mock_get:
            mock_get.return_value = {"status": "pending", "text": "test"}

            # Mock set_job_status
            with mock.patch.object(client, "set_job_status") as mock_set:
                client.update_job_status("transcription", "test-id", "done")

                mock_get.assert_called_once_with("transcription", "test-id")
                mock_set.assert_called_once_with(
                    "transcription",
                    "test-id",
                    "done",
                    {"status": "done", "text": "test"},
                )

    def test_update_job_status_not_existing(self, mock_redis_conn):
        """Test updating job status for non-existing job."""
        client = RedisClient()

        # Mock get_job_status to return None
        with mock.patch.object(client, "get_job_status") as mock_get:
            mock_get.return_value = None

            # Mock set_job_status
            with mock.patch.object(client, "set_job_status") as mock_set:
                client.update_job_status("transcription", "test-id", "done")

                mock_get.assert_called_once_with("transcription", "test-id")
                mock_set.assert_called_once_with("transcription", "test-id", "done")


# Status manager tests
class TestStatusManager:
    """Tests for StatusManager class."""

    @pytest.fixture
    def mock_redis_client(self):
        """Mock RedisClient."""
        return mock.MagicMock(spec=RedisClient)

    def test_set_pending(self, mock_redis_client):
        """Test setting pending status."""
        manager = StatusManager(mock_redis_client)
        manager.set_pending("transcription", "test-id")

        mock_redis_client.set_job_status.assert_called_once_with(
            "transcription", "test-id", JobStatus.PENDING
        )

    def test_set_working(self, mock_redis_client):
        """Test setting working status."""
        manager = StatusManager(mock_redis_client)
        manager.set_working("transcription", "test-id")

        mock_redis_client.update_job_status.assert_called_once_with(
            "transcription", "test-id", JobStatus.WORKING
        )

    def test_set_done(self, mock_redis_client):
        """Test setting done status with result."""
        manager = StatusManager(mock_redis_client)
        result = {"text": "test result"}

        with mock.patch("src.common.status.datetime") as mock_datetime:
            # Mock datetime.utcnow() and timedelta
            mock_now = mock.MagicMock()
            mock_datetime.utcnow.return_value = mock_now
            # mock_now + mock.ANY = mock_now  # Mock addition
            mock_now.isoformat.return_value = "2025-04-17T00:00:00"

            manager.set_done("transcription", "test-id", result)

            # Check that set_job_status was called with the right arguments
            mock_redis_client.set_job_status.assert_called_once()
            call_args = mock_redis_client.set_job_status.call_args[0]
            assert call_args[0] == "transcription"
            assert call_args[1] == "test-id"
            assert call_args[2] == JobStatus.DONE
            assert "text" in call_args[3]
            assert call_args[3]["text"] == "test result"
            assert "expires_at" in call_args[3]

    def test_set_error(self, mock_redis_client):
        """Test setting error status."""
        manager = StatusManager(mock_redis_client)
        manager.set_error("transcription", "test-id", "TestError")

        mock_redis_client.set_job_status.assert_called_once()
        call_args = mock_redis_client.set_job_status.call_args[0]
        assert call_args[0] == "transcription"
        assert call_args[1] == "test-id"
        assert call_args[2] == JobStatus.ERROR
        assert call_args[3]["error"] == "TestError"

    def test_get_status(self, mock_redis_client):
        """Test getting status."""
        manager = StatusManager(mock_redis_client)
        mock_redis_client.get_job_status.return_value = {
            "status": "done",
            "text": "test",
        }

        result = manager.get_status("transcription", "test-id")

        assert result == {"status": "done", "text": "test"}
        mock_redis_client.get_job_status.assert_called_once_with(
            "transcription", "test-id"
        )
