"""
Tests for worker and scheduler modules.
"""

import os
import sys
from unittest import mock

import pytest
import redis
from rq import Queue, Worker
from rq_scheduler import Scheduler  # type: ignore

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.scheduler import (
    cleanup_expired_keys,
    cleanup_transcription_uploads,
    start_scheduler,
)
from src.worker import start_worker


# Tests for worker module
class TestWorker:
    """Tests for worker module."""

    @pytest.fixture
    def mock_redis_class(self):
        """Mock for redis.Redis class."""
        with mock.patch("src.worker.redis.Redis") as mock_redis:
            yield mock_redis

    @pytest.fixture
    def mock_worker_class(self):
        """Mock for rq.Worker class."""
        with mock.patch("src.worker.Worker") as mock_worker:
            yield mock_worker

    @pytest.fixture
    def mock_connection(self):
        """Mock for rq.Connection context manager."""
        mock_cm = mock.MagicMock()
        mock_cm.__enter__.return_value = None
        mock_cm.__exit__.return_value = None

        with mock.patch(
            "src.worker.Connection", return_value=mock_cm
        ) as mock_connection:
            yield mock_connection

    def test_start_worker(self, mock_redis_class, mock_worker_class, mock_connection):
        """Test start_worker function."""
        # Configure mocks
        mock_redis_instance = mock.MagicMock()
        mock_redis_class.return_value = mock_redis_instance

        mock_worker_instance = mock.MagicMock()
        mock_worker_class.return_value = mock_worker_instance

        # Call function
        start_worker()

        # Verify Redis connection was created
        mock_redis_class.assert_called_once_with(host="localhost", port=6379, db=0)

        # Verify Worker was created and started
        mock_worker_class.assert_called_once_with(["default"])
        mock_worker_instance.work.assert_called_once()

    def test_start_worker_error(
        self, mock_redis_class, mock_worker_class, mock_connection
    ):
        """Test start_worker function with error."""
        # Configure mocks to raise an exception
        mock_redis_class.side_effect = Exception("Test error")

        # Call function with sys.exit mocked
        with mock.patch("sys.exit") as mock_exit:
            start_worker()

            # Verify sys.exit was called
            mock_exit.assert_called_once_with(1)


# Tests for scheduler module
class TestScheduler:
    """Tests for scheduler module."""

    @pytest.fixture
    def mock_redis_class(self):
        """Mock for redis.Redis class."""
        with mock.patch("src.scheduler.redis.Redis") as mock_redis:
            yield mock_redis

    @pytest.fixture
    def mock_scheduler_class(self):
        """Mock for rq_scheduler.Scheduler class."""
        with mock.patch("src.scheduler.Scheduler") as mock_scheduler:
            yield mock_scheduler

    def test_cleanup_transcription_uploads_dir_not_exists(self):
        """Test cleanup_transcription_uploads when directory doesn't exist."""
        # Mock Path.exists to return False
        with mock.patch("src.scheduler.Path.exists", return_value=False):
            # Call function
            cleanup_transcription_uploads()

            # No exception should be raised

    def test_cleanup_transcription_uploads(self, mock_redis_class):
        """Test cleanup_transcription_uploads."""
        # Configure mocks
        mock_redis_instance = mock.MagicMock()
        mock_redis_class.return_value = mock_redis_instance

        # Mock exists to return True
        with mock.patch("src.scheduler.Path.exists", return_value=True):
            # Mock iterdir to return some directories
            mock_dir1 = mock.MagicMock()
            mock_dir1.is_dir.return_value = True
            mock_dir1.name = "dir1"

            mock_dir2 = mock.MagicMock()
            mock_dir2.is_dir.return_value = True
            mock_dir2.name = "dir2"

            mock_file = mock.MagicMock()
            mock_file.is_dir.return_value = False
            mock_file.name = "file"

            with mock.patch(
                "src.scheduler.Path.iterdir",
                return_value=[mock_dir1, mock_dir2, mock_file],
            ):
                # Configure Redis mock
                mock_redis_instance.exists.side_effect = (
                    lambda key: key == "transcription:dir1"
                )

                # Mock shutil.rmtree
                with mock.patch("src.scheduler.shutil.rmtree") as mock_rmtree:
                    # Call function
                    cleanup_transcription_uploads()

                    # Verify Redis.exists was called
                    assert mock_redis_instance.exists.call_count == 2
                    mock_redis_instance.exists.assert_any_call("transcription:dir1")
                    mock_redis_instance.exists.assert_any_call("transcription:dir2")

                    # Verify shutil.rmtree was called for dir2 only
                    mock_rmtree.assert_called_once_with(mock_dir2)

    def test_cleanup_expired_keys(self):
        """Test cleanup_expired_keys."""
        # This function doesn't do much yet, just verify it runs without error
        cleanup_expired_keys()

    def test_start_scheduler(self, mock_redis_class, mock_scheduler_class):
        """Test start_scheduler function."""
        # Configure mocks
        mock_redis_instance = mock.MagicMock()
        mock_redis_class.return_value = mock_redis_instance

        mock_scheduler_instance = mock.MagicMock()
        mock_scheduler_class.return_value = mock_scheduler_instance

        # Mock scheduler.get_jobs
        mock_job1 = mock.MagicMock()
        mock_job2 = mock.MagicMock()
        mock_scheduler_instance.get_jobs.return_value = [mock_job1, mock_job2]

        # Call function
        start_scheduler()

        # Verify Redis connection was created
        mock_redis_class.assert_called_once_with(host="localhost", port=6379, db=0)

        # Verify Scheduler was created
        mock_scheduler_class.assert_called_once_with(connection=mock_redis_instance)

        # Verify existing jobs were cancelled
        assert mock_scheduler_instance.cancel.call_count == 2
        mock_scheduler_instance.cancel.assert_any_call(mock_job1)
        mock_scheduler_instance.cancel.assert_any_call(mock_job2)

        # Verify new jobs were scheduled
        assert mock_scheduler_instance.cron.call_count == 2

        # Verify scheduler was run
        mock_scheduler_instance.run.assert_called_once()

    def test_start_scheduler_error(self, mock_redis_class, mock_scheduler_class):
        """Test start_scheduler function with error."""
        # Configure mocks to raise an exception
        mock_redis_class.side_effect = Exception("Test error")

        # Call function with sys.exit mocked
        with mock.patch("sys.exit") as mock_exit:
            start_scheduler()

            # Verify sys.exit was called
            mock_exit.assert_called_once_with(1)
