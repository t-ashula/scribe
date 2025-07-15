"""
Transcription model implementation.
"""

import time
from typing import Any, Dict, List

import torch
from transformers import pipeline


def transcribe_with_model(file_name: str, language: str = "ja") -> Dict[str, Any]:
    """
    Transcribe audio file using a pre-trained model.

    Args:
        file_name: Path to the audio file
        language: Language code (e.g., ja)

    Returns:
        Dictionary containing the transcription result
    """
    return _transcribe_with_kotoba_whisper(file_name, language)


def _transcribe_with_kotoba_whisper(
    file_name: str, language: str = "ja"
) -> Dict[str, Any]:
    """
    Transcribe audio file using Kotoba Whisper model.

    Args:
        file_name: Path to the audio file
        language: Language code (e.g., ja)

    Returns:
        Dictionary containing the transcription result
    """
    # config
    model_id = "kotoba-tech/kotoba-whisper-v1.1"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    model_kwargs = {"attn_implementation": "sdpa"} if torch.cuda.is_available() else {}

    # load model
    pipe = pipeline(
        "automatic-speech-recognition",
        model=model_id,
        torch_dtype=torch_dtype,
        device=device,
        model_kwargs=model_kwargs,
        chunk_length_s=15,
        batch_size=16,
        trust_remote_code=True,
        stable_ts=True,
        punctuator=True,
    )

    # Set language for generation
    lang_map = {
        "ja": "japanese",
        "en": "english",
        # Add more languages as needed
    }
    model_language = lang_map.get(language, "japanese")

    generate_kwargs = {"language": model_language, "task": "transcribe"}

    # Process audio file
    start_time = time.time()
    result = pipe(file_name, return_timestamps=True, generate_kwargs=generate_kwargs)
    process_time = time.time() - start_time

    # Extract segments with timestamps
    if isinstance(result, dict):
        chunks = result.get("chunks", [])
        text = result.get("text", "")
    else:
        chunks = result if isinstance(result, list) else []
        text = " ".join([chunk.get("text", "") for chunk in chunks]) if chunks else ""
    
    segments = list(
        map(
            lambda c: {
                "start": c.get("timestamp", [0, 0])[0] if c.get("timestamp") else 0,
                "end": c.get("timestamp", [0, 0])[1] if c.get("timestamp") else 0,
                "text": c.get("text", ""),
            },
            chunks,
        )
    )

    return {
        "text": text,
        "lang": language,
        "segments": segments,
        "stats": {"process_time": process_time},
    }
