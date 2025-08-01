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
ALIGN_MODEL_PATH = os.path.join(os.path.dirname(__file__), "align_0.1.pt")  # Relative to script location

def main():
    print(f"Transcribing '{input_path}' using WhisperX model '{MODEL_SIZE}' on device '{DEVICE}'...")
    # Load WhisperX ASR model
    asr_model = whisperx.load_model(MODEL_SIZE, DEVICE, compute_type="float16" if DEVICE == "cuda" else "float32")

    # STEP 1: Transcribe with ASR
    asr_result = asr_model.transcribe(input_path)
    segments = asr_result["segments"]  # list of sentence-level segments with 'start', 'end', 'text'

    print(f"Initial segment count: {len(segments)}")

    # STEP 2: Align to get word-level timestamps with downloaded model if available
    print("(Loading align model...)")
    # Print the alignment model path for transparency
    print(f"Alignment model path being used: {ALIGN_MODEL_PATH}")
    # Updated: Remove unsupported `model_fp` argument for compatibility with currently installed whisperx
    # If you are using a non-standard path for the model, you must move or symlink it as required.
    align_model, metadata = whisperx.load_align_model(language_code="en", device=DEVICE)
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
