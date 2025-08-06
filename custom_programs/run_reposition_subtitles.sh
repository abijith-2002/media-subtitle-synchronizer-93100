#!/bin/bash
# Script to run Reposition_subtitles.py with preset inputs and outputs

# Absolute/relative paths, assuming script is run from project root or adjust as needed
PYTHON_SCRIPT="Reposition_subtitles.py"
VIDEO_INPUT="output2.mp4"
SRT_INPUT="Key_and_Peele_sample1.srt"
OUTPUT_FILE="repositioned_subtitles.ass"

# Set the working directory to the location of this script for safety
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Execute the Python script
python3 "$PYTHON_SCRIPT" --video "$VIDEO_INPUT" --srt "$SRT_INPUT" --output "$OUTPUT_FILE"
