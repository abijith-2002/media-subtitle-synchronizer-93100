#!/usr/bin/env python3
"""
download_whisperx_align_model.py

Script to download the default English alignment model (align_0.1.pt) used by WhisperX
from the official HuggingFace repository into the current directory.

Usage:
    python download_whisperx_align_model.py

This downloads 'align_0.1.pt' to the same directory as this script.
"""

import os
import sys

MODEL_URL = "https://huggingface.co/pyannote/segmentation/resolve/main/models/align_0.1.pt"
MODEL_FILENAME = "align_0.1.pt"

def download_model(url: str, filename: str, overwrite: bool = False):
    """
    Downloads the model from the specified URL to the given filename.
    Checks for file existence and skips download unless overwrite=True.
    """
    # Attempt to use requests, fallback to urllib if unavailable
    try:
        import requests
        if not overwrite and os.path.exists(filename):
            print(f"File '{filename}' already exists. Skipping download.")
            return
        print(f"Downloading WhisperX alignment model from {url} ...")
        resp = requests.get(url, stream=True)
        resp.raise_for_status()
        with open(filename, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"Model downloaded successfully as '{filename}'.")
    except ImportError:
        # Pure stdlib fallback
        import urllib.request
        if not overwrite and os.path.exists(filename):
            print(f"File '{filename}' already exists. Skipping download.")
            return
        print(f"Downloading WhisperX alignment model from {url} ...")
        with urllib.request.urlopen(url) as response, open(filename, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        print(f"Model downloaded successfully as '{filename}'.")

if __name__ == "__main__":
    overwrite = False
    if len(sys.argv) > 1 and sys.argv[1] == "--overwrite":
        overwrite = True
    download_model(MODEL_URL, MODEL_FILENAME, overwrite=overwrite)
