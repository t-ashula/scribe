"""
Summarization model implementation.
"""

import logging
import time
from typing import Any, Dict

import torch
from transformers import pipeline

# Logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("summarizer")


def summarize_with_model(text: str, strength: int) -> Dict[str, Any]:
    """
    Summarize text using a pre-trained model.

    Args:
        text: Text to summarize
        strength: Summarization strength (1-5)

    Returns:
        Dictionary containing the summarization result
    """
    # Map strength to max_length
    # 1: very short summary, 5: longer summary
    max_length_map = {
        1: 100,  # Very concise
        2: 150,  # Concise
        3: 200,  # Moderate
        4: 300,  # Detailed
        5: 400,  # Very detailed
    }
    max_length = max_length_map.get(strength, 200)  # Default to 3 if invalid

    # For now, we'll use a simple implementation with transformers
    return _summarize_with_transformers(text, max_length)


def _summarize_with_transformers(text: str, max_length: int) -> Dict[str, Any]:
    """
    Summarize text using the transformers library.

    Args:
        text: Text to summarize
        max_length: Maximum length of the summary

    Returns:
        Dictionary containing the summarization result
    """
    # Config
    model_id = "facebook/bart-large-cnn"  # Example model, can be replaced with a Japanese model
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    device = "cuda:0" if torch.cuda.is_available() else "cpu"

    logger.info(f"Using device: {device}, model: {model_id}")

    # Load model
    start_time = time.time()

    try:
        summarizer = pipeline(
            "summarization",
            model=model_id,
            torch_dtype=torch_dtype,
            device=device,
        )

        # Generate summary
        result = summarizer(
            text,
            max_length=max_length,
            min_length=max(
                30, max_length // 4
            ),  # Min length is 1/4 of max or at least 30
            do_sample=False,
        )

        process_time = time.time() - start_time

        # Extract summary text from result
        summary = result[0]["summary_text"] if result else "Failed to generate summary."

        return {
            "summary": summary,
            "stats": {
                "process_time": process_time,
                "model": model_id,
                "max_length": max_length,
            },
        }

    except Exception as e:
        logger.error(f"Error in summarization: {str(e)}")
        process_time = time.time() - start_time

        # Return a fallback summary for development/testing
        return {
            "summary": f"Error occurred in summarization model. As this is in development, returning the first {max_length//10} characters of the text: {text[:max_length//10]}...",
            "stats": {
                "process_time": process_time,
                "error": str(e),
            },
        }
