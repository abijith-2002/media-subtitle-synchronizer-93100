# src/whisperx_integration.py
"""Integration with WhisperX model for subtitle processing."""

from typing import List

# PUBLIC_INTERFACE
def run_whisperx_on_file(input_path: str) -> List[dict]:
    """
    Simulated WhisperX interface. In production, call actual WhisperX with subprocess or as library.
    Returns: List of subtitle dicts {start, end, text}
    """
    # Example dummy output, replace with actual call
    return [
        {"start": 0.0, "end": 2.5, "text": "Hello, this is a test."},
        {"start": 2.5, "end": 5.0, "text": "This is another line of subtitle."}
    ]
