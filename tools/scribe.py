#!/usr/bin/env python
"""
CLI tool for Scribe package.
This tool is intended for development use only.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir.resolve()))

# Import after path modification to avoid E402
from src.summarization.model import summarize_with_model  # noqa: E402
from src.transcription.model import transcribe_with_model  # noqa: E402


def transcribe_command(args: argparse.Namespace) -> None:
    """
    Handle transcribe command.
    """
    print(f"Transcribing file: {args.file}")
    print(f"Language: {args.language}")

    try:
        result = transcribe_with_model(args.file, args.language)
        output_result(result, args.output)
    except Exception as e:
        print(f"Error during transcription: {e}", file=sys.stderr)
        sys.exit(1)


def summarize_command(args: argparse.Namespace) -> None:
    """
    Handle summarize command.
    """
    # Read input text
    if args.file:
        try:
            with open(args.file, encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Read from stdin if no file is provided
        print(
            "Reading text from stdin. Press Ctrl+D (Unix) or Ctrl+Z (Windows) "
            "when finished."
        )
        text = sys.stdin.read()

    if not text.strip():
        print("Error: Empty text input", file=sys.stderr)
        sys.exit(1)

    print(f"Summarizing text ({len(text)} characters)")
    print(f"Strength: {args.strength}")

    try:
        result = summarize_with_model(text, args.strength)
        output_result(result, args.output)
    except Exception as e:
        print(f"Error during summarization: {e}", file=sys.stderr)
        sys.exit(1)


def output_result(result: dict[str, Any], output_file: str | None = None) -> None:
    """
    Output the result to file or stdout.
    """
    # Format the result as JSON
    formatted_result = json.dumps(result, ensure_ascii=False, indent=2)

    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(formatted_result)
            print(f"Result saved to {output_file}")
        except Exception as e:
            print(f"Error writing to output file: {e}", file=sys.stderr)
            print("Printing result to stdout instead:")
            print(formatted_result)
    else:
        print(formatted_result)


def main() -> None:
    """
    Main entry point for the CLI.
    """
    parser = argparse.ArgumentParser(
        description="Scribe CLI tool for development use",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Transcribe command
    transcribe_parser = subparsers.add_parser(
        "transcribe", help="Transcribe an audio file"
    )
    transcribe_parser.add_argument("file", help="Path to the audio file to transcribe")
    transcribe_parser.add_argument(
        "--language", "-l", default="ja", help="Language code (e.g., ja, en)"
    )
    transcribe_parser.add_argument(
        "--output", "-o", help="Output file path (default: stdout)"
    )
    transcribe_parser.set_defaults(func=transcribe_command)

    # Summarize command
    summarize_parser = subparsers.add_parser("summarize", help="Summarize text")
    summarize_parser.add_argument(
        "--file",
        "-f",
        help="Path to the text file to summarize (if not provided, reads from stdin)",
    )
    summarize_parser.add_argument(
        "--strength",
        "-s",
        type=int,
        default=3,
        choices=range(1, 6),
        help="Summarization strength (1: very concise, 5: very detailed)",
    )
    summarize_parser.add_argument(
        "--output", "-o", help="Output file path (default: stdout)"
    )
    summarize_parser.set_defaults(func=summarize_command)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Execute the appropriate command
    args.func(args)


if __name__ == "__main__":
    main()
