#!/bin/bash

# Shell script to run the Reposition_subtitles.py script with specified input arguments
# Usage: ./run_reposition_subtitles.sh

VIDEO_PATH="output2.mp4"
SRT_PATH="Key_and_Peele_sample1.srt"
OUTPUT_ASS="repositioned_subtitles.ass"

# Run the Python script to reposition subtitles
python3 Reposition_subtitles.py --video_path "$VIDEO_PATH" --srt_path "$SRT_PATH" --output "$OUTPUT_ASS"
