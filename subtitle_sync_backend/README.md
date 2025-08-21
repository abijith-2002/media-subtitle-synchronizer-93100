# Subtitle Sync Backend

FastAPI backend for uploading media, processing subtitles via WhisperX (stubbed), database tracking, and subtitle retrieval.

## Features
- Upload audio/video files
- Background processing (WhisperX integration placeholder)
- Check processing status
- Download generated subtitles
- List uploaded files
- Theme hint for docs via `theme` query param or `X-Theme` header

## Environment Variables (see .env.example)
- UPLOAD_DIR: Directory to store uploaded media
- SUBTITLE_DIR: Directory to store generated subtitles
- ALLOWED_EXTENSIONS: Comma-separated allowed extensions (e.g., `.mp3,.mp4,.mkv`)
- POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD: PostgreSQL connection details
- WHISPERX_MODEL, WHISPERX_LANGUAGE: Model settings for WhisperX
- DEBUG: Enable verbose logging (true/false)

## Endpoints
- POST /upload: Upload media and start processing
- GET /status?id=UUID: Check processing status
- GET /subtitles?id=UUID[&download=true]: Get or download subtitles
- GET /files: List uploaded files
- GET /websocket-docs: Info about future WebSocket support

## Running Locally
1. Create and configure a PostgreSQL database.
2. Copy `.env.example` to `.env` and adjust values.
3. Install requirements: `pip install -r requirements.txt`
4. Start the server: `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
5. Open docs: http://localhost:8000/docs

Note: WhisperX integration is stubbed. Replace the `_simulate_whisperx_generate_srt` function in `src/api/services/processing.py` with real WhisperX calls in a production setup.
