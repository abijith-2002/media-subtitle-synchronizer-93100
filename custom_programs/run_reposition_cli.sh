#!/bin/bash

# Run the subtitle repositioning Python script with CLI arguments
python3 Reposition_subtitles.py \
  --video_path output2.mp4 \
  --srt_path Key_and_Peele_sample1.srt \
  --output_path repositioned_subtitles.ass
