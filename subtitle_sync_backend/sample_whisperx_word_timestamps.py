#!/usr/bin/env python3
"""
sample_whisperx_word_timestamps.py

Sample script to demonstrate word-level timestamp extraction using WhisperX.

This script accepts a path to a video or audio file as a command-line argument,
runs WhisperX ASR & alignment to extract word-level timings, and prints the results as:
    [start_time, end_time]  word

Dependencies:
    - torch
    - whisperx

To install dependencies:
    pip install torch whisperx

To download the English alignment model (align_0.1.pt) to the current directory, run:
    python download_whisperx_align_model.py

Usage:
    python sample_whisperx_word_timestamps.py path/to/audio_or_video_file

If you have the align_0.1.pt file in the current directory, it will be used for alignment.
"""

import sys
import os

def print_usage():
    print("Usage: python sample_whisperx_word_timestamps.py <path/to/audio_or_video_file>")
    print("For best results, ensure 'align_0.1.pt' exists in this directory (see script header).")
    sys.exit(1)

# Make sure user supplied a file argument
if len(sys.argv) != 2:
    print_usage()

input_path = sys.argv[1]
if not os.path.isfile(input_path):
    print(f"ERROR: File '{input_path}' does not exist.")
    sys.exit(1)

# Import dependencies (with error message if missing)
try:
    import torch
    import whisperx
except ImportError:
    print("Missing dependency! Please install with: pip install torch whisperx")
    sys.exit(1)

# ---- CONFIG ----
# You may adjust these for other models/languages
MODEL_SIZE = "base"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# Note: ALIGN_MODEL_PATH is not required when allowing WhisperX to choose the default,
# but we keep it for reference in comments/documentation.
ALIGN_MODEL_PATH = os.path.join(os.path.dirname(__file__), "align_0.1.pt")  # Relative to script location

def main():
    print(f"Transcribing '{input_path}' using WhisperX model '{MODEL_SIZE}' on device '{DEVICE}'...")
    # Load WhisperX ASR model
    asr_model = whisperx.load_model(MODEL_SIZE, DEVICE, compute_type="float16" if DEVICE == "cuda" else "float32")

    # STEP 1: Transcribe with ASR
    asr_result = asr_model.transcribe(input_path)
    segments = asr_result["segments"]  # list of sentence-level segments with 'start', 'end', 'text'

    print(f"Initial segment count: {len(segments)}")

    # STEP 2: Align to get word-level timestamps, allowing WhisperX to handle model loading location.
    print("(Loading align model...)")
    align_model, metadata = whisperx.load_align_model(language_code="en", device=DEVICE)
    # Attempt to print the model path in use, if available
    align_model_path = None
    # Try several likely locations in returned objects to print the model path, if exposed by the loaded object
    if hasattr(align_model, "model_file"):
        align_model_path = getattr(align_model, "model_file", None)
    elif hasattr(align_model, "model_path"):
        align_model_path = getattr(align_model, "model_path", None)
    # Sometimes it's in a submodule or an attribute (for pyannote style torch models)
    elif hasattr(align_model, "file"):
        align_model_path = getattr(align_model, "file", None)
    elif hasattr(align_model, "model") and hasattr(align_model.model, "file"):
        align_model_path = getattr(align_model.model, "file", None)
    # Some versions may set the path in the metadata dictionary
    elif isinstance(metadata, dict) and "model_path" in metadata:
        align_model_path = metadata["model_path"]
    # Print the discovered model path
    if align_model_path:
        print(f"Actual alignment model file in use: {align_model_path}")
    else:
        print("Alignment model path info not available in align_model object; using WhisperX default.")

    word_segments = whisperx.align(segments, align_model, metadata, input_path, device=DEVICE, return_char_alignments=False)
    
    # STEP 3: Print out word-level alignments
    print("\nWord-level alignments:\n-----------------------------")
    for word in word_segments:
        # Handle both dict and string case for backward compatibility or unexpected outputs
        if isinstance(word, dict):
            text = word.get("text", "<unk>")
            start = word.get("start", None)
            end = word.get("end", None)
            if start is not None and end is not None:
                print(f"[{start:.2f}, {end:.2f}]   {text}")
            else:
                print(f"[??, ??]   {text}")
        else:
            # If word is just a string
            print(f"[??, ??]   {str(word)}")
    print("\nDone.")

if __name__ == "__main__":
    main()
