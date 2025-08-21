# Project Repository

This is the initial README file for the project.

## Subtitle Sync Backend

FastAPI backend to upload media, run WhisperX to generate synchronized subtitles, store results in PostgreSQL, and provide REST endpoints.

### Features
- File upload for audio/video: POST /upload
- View processing status: GET /status/{job_id}
- Retrieve structured subtitles: GET /subtitles/{job_id}
- Download files: 
  - GET /files/{job_id} 
  - GET /files/{job_id}/original 
  - GET /files/{job_id}/subtitle
- User theme preferences: 
  - GET /preferences/theme?user_id=... 
  - POST /preferences/theme

### Configuration
Copy `.env.example` to `.env` and set:
- DATABASE_URL (use PostgreSQL in production)
- UPLOAD_DIR, SUBTITLE_DIR
- CORS_ALLOW_ORIGINS

### Run
Install requirements and start the app:
```
pip install -r subtitle_sync_backend/requirements.txt
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 3001 --app-dir subtitle_sync_backend
```

Generate OpenAPI file:
```
python -m src.api.generate_openapi
```

Note: WhisperX is mocked here; integrate the real model in `run_whisperx_generate_subtitles`.
