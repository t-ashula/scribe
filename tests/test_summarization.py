"""
Tests for summarization module.
"""

import os
import sys
from unittest import mock

import pytest

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.common.models import JobType
from src.summarization.model import summarize_with_model
from src.summarization.processor import SummarizationProcessor


# Mock for transformers pipeline
@pytest.fixture
def mock_pipeline():
    """Mock for transformers pipeline."""
    with mock.patch("src.summarization.model.pipeline") as mock_pipeline:
        # Create mock pipeline instance
        mock_pipe = mock.MagicMock()
        mock_pipeline.return_value = mock_pipe

        # Configure mock pipe to return a result when called
        mock_result = [{"summary_text": "This is a test summary."}]
        mock_pipe.return_value = mock_result

        yield mock_pipeline


# Mock for torch
@pytest.fixture
def mock_torch():
    """Mock for torch."""
    with mock.patch("src.summarization.model.torch") as mock_torch:
        # Configure mock torch.cuda.is_available
        mock_torch.cuda.is_available.return_value = False
        mock_torch.float32 = "float32"  # Mock float32 attribute

        yield mock_torch


# Tests for summarization model
class TestSummarizationModel:
    """Tests for summarization model."""

    def test_summarize_with_model(self, mock_pipeline, mock_torch):
        """Test summarize_with_model function."""
        # Call function
        result = summarize_with_model("This is a test text for summarization.", 3)

        # Verify pipeline was created with correct parameters
        mock_pipeline.assert_called_once()
        call_args = mock_pipeline.call_args[1]
        assert call_args["model"] == "facebook/bart-large-cnn"
        assert call_args["torch_dtype"] == "float32"
        assert call_args["device"] == "cpu"

        # Verify pipeline was called with correct parameters
        mock_pipe = mock_pipeline.return_value
        mock_pipe.assert_called_once()
        assert mock_pipe.call_args[0][0] == "This is a test text for summarization."
        assert mock_pipe.call_args[1]["max_length"] == 200  # Strength 3 = 200

        # Verify result
        assert result["summary"] == "This is a test summary."
        assert "stats" in result
        assert "process_time" in result["stats"]
        assert "model" in result["stats"]
        assert "max_length" in result["stats"]

    def test_summarize_with_model_different_strengths(self, mock_pipeline, mock_torch):
        """Test summarize_with_model with different strengths."""
        # Test with strength 1 (very concise)
        summarize_with_model("This is a test text for summarization.", 1)
        assert mock_pipeline.return_value.call_args[1]["max_length"] == 100

        # Test with strength 5 (very detailed)
        summarize_with_model("This is a test text for summarization.", 5)
        assert mock_pipeline.return_value.call_args[1]["max_length"] == 400

    def test_summarize_with_model_error(self, mock_pipeline, mock_torch):
        """Test summarize_with_model with error."""
        # Configure mock_pipe to raise an exception
        mock_pipeline.return_value.side_effect = RuntimeError("Test error")

        # Call function
        result = summarize_with_model("This is a test text for summarization.", 3)

        # Verify result contains error information
        assert "summary" in result
        assert "Error occurred" in result["summary"]
        assert "stats" in result
        assert "error" in result["stats"]
        assert "Test error" in result["stats"]["error"]


# Tests for summarization processor
class TestSummarizationProcessor:
    """Tests for SummarizationProcessor class."""

    @pytest.fixture
    def processor(self):
        """Create SummarizationProcessor instance."""
        return SummarizationProcessor(JobType.SUMMARIZATION, "test-id")

    def test_validate_input_valid(self, processor):
        """Test validate_input with valid input."""
        # Call validate_input
        processor.validate_input(
            text="This is a test text for summarization.", strength=3
        )

        # No exception should be raised

    def test_validate_input_empty_text(self, processor):
        """Test validate_input with empty text."""
        # Call validate_input
        with pytest.raises(ValueError):
            processor.validate_input(text="", strength=3)

    def test_validate_input_invalid_text(self, processor):
        """Test validate_input with invalid text."""
        # Call validate_input
        with pytest.raises(ValueError):
            processor.validate_input(text=123, strength=3)  # Not a string

    def test_validate_input_invalid_strength(self, processor):
        """Test validate_input with invalid strength."""
        # Call validate_input with strength too low
        with pytest.raises(ValueError):
            processor.validate_input(
                text="This is a test text for summarization.", strength=0
            )

        # Call validate_input with strength too high
        with pytest.raises(ValueError):
            processor.validate_input(
                text="This is a test text for summarization.", strength=6
            )

        # Call validate_input with non-integer strength
        with pytest.raises(ValueError):
            processor.validate_input(
                text="This is a test text for summarization.", strength="3"
            )

    @mock.patch("src.summarization.processor.summarize_with_model")
    def test_execute(self, mock_summarize, processor):
        """Test execute method."""
        # Configure mock_summarize
        mock_summarize.return_value = {
            "summary": "This is a test summary.",
            "stats": {"process_time": 1.0, "model": "test-model", "max_length": 200},
        }

        # Call execute
        result = processor.execute(
            text="This is a test text for summarization.", strength=3
        )

        # Verify summarize_with_model was called
        mock_summarize.assert_called_once_with(
            "This is a test text for summarization.", 3
        )

        # Verify result
        assert result["summary"] == "This is a test summary."
        assert result["stats"] == {
            "process_time": 1.0,
            "model": "test-model",
            "max_length": 200,
        }
