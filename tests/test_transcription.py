"""
Tests for transcription module.
"""

import os
import sys
from unittest import mock

import pytest

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.common.models import JobType
from src.transcription.model import transcribe_with_model
from src.transcription.processor import TranscriptionProcessor


# Mock for transformers pipeline
@pytest.fixture
def mock_pipeline():
    """Mock for transformers pipeline."""
    with mock.patch("src.transcription.model.pipeline") as mock_pipeline:
        # Create mock pipeline instance
        mock_pipe = mock.MagicMock()
        mock_pipeline.return_value = mock_pipe

        # Configure mock pipe to return a result when called
        mock_result = {
            "text": "This is a test transcription.",
            "chunks": [
                {"timestamp": [0.0, 1.0], "text": "This is"},
                {"timestamp": [1.0, 2.0], "text": "a test transcription."},
            ],
        }
        mock_pipe.return_value = mock_result

        yield mock_pipeline


# Mock for torch
@pytest.fixture
def mock_torch():
    """Mock for torch."""
    with mock.patch("src.transcription.model.torch") as mock_torch:
        # Configure mock torch.cuda.is_available
        mock_torch.cuda.is_available.return_value = False
        mock_torch.float32 = "float32"  # Mock float32 attribute

        yield mock_torch


# Tests for transcription model
class TestTranscriptionModel:
    """Tests for transcription model."""

    def test_transcribe_with_model(self, mock_pipeline, mock_torch):
        """Test transcribe_with_model function."""
        # Call function
        result = transcribe_with_model("test.wav", "ja")

        # Verify pipeline was created with correct parameters
        mock_pipeline.assert_called_once()
        call_args = mock_pipeline.call_args[1]
        assert call_args["model"] == "kotoba-tech/kotoba-whisper-v1.1"
        assert call_args["torch_dtype"] == "float32"
        assert call_args["device"] == "cpu"

        # Verify pipeline was called with correct parameters
        mock_pipe = mock_pipeline.return_value
        mock_pipe.assert_called_once()
        assert mock_pipe.call_args[0][0] == "test.wav"
        assert mock_pipe.call_args[1]["return_timestamps"] is True
        assert mock_pipe.call_args[1]["generate_kwargs"] == {
            "language": "japanese",
            "task": "transcribe",
        }

        # Verify result
        assert result["text"] == "This is a test transcription."
        assert result["lang"] == "ja"
        assert len(result["segments"]) == 2
        assert result["segments"][0]["start"] == 0.0
        assert result["segments"][0]["end"] == 1.0
        assert result["segments"][0]["text"] == "This is"
        assert "stats" in result
        assert "process_time" in result["stats"]


# Tests for transcription processor
class TestTranscriptionProcessor:
    """Tests for TranscriptionProcessor class."""

    @pytest.fixture
    def processor(self):
        """Create TranscriptionProcessor instance."""
        return TranscriptionProcessor(JobType.TRANSCRIPTION, "test-id")

    def test_validate_input_valid(self, processor):
        """Test validate_input with valid input."""
        # Create test file
        test_file = "test.wav"

        # Mock Path.exists to return True
        with mock.patch("pathlib.Path.exists", return_value=True):
            # Call validate_input
            processor.validate_input(file_path=test_file, language="ja", model="base")

            # No exception should be raised

    def test_validate_input_file_not_found(self, processor):
        """Test validate_input with non-existent file."""
        # Create test file
        test_file = "nonexistent.wav"

        # Mock Path.exists to return False
        with mock.patch("pathlib.Path.exists", return_value=False):
            # Call validate_input
            with pytest.raises(FileNotFoundError):
                processor.validate_input(
                    file_path=test_file, language="ja", model="base"
                )

    def test_validate_input_invalid_language(self, processor):
        """Test validate_input with invalid language."""
        # Create test file
        test_file = "test.wav"

        # Mock Path.exists to return True
        with mock.patch("pathlib.Path.exists", return_value=True):
            # Call validate_input
            with pytest.raises(ValueError):
                processor.validate_input(
                    file_path=test_file, language="invalid", model="base"
                )

    @mock.patch("src.transcription.processor.transcribe_with_model")
    def test_execute(self, mock_transcribe, processor):
        """Test execute method."""
        # Configure mock_transcribe
        mock_transcribe.return_value = {
            "text": "This is a test transcription.",
            "lang": "ja",
            "segments": [{"start": 0.0, "end": 1.0, "text": "This is a test."}],
            "stats": {"process_time": 1.0},
        }

        # Call execute
        result = processor.execute(file_path="test.wav", language="ja", model="base")

        # Verify transcribe_with_model was called
        mock_transcribe.assert_called_once_with("test.wav", "ja")

        # Verify result
        assert result["text"] == "This is a test transcription."
        assert result["segments"] == [
            {"start": 0.0, "end": 1.0, "text": "This is a test."}
        ]
        assert result["stats"] == {"process_time": 1.0}
