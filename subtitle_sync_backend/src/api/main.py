from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import shutil
import os
import uuid

from .models import FileUploadResponse, StatusResponse, SubtitlesResponse, SubtitleLine, ListFilesResponse
from .db import save_file_processing_status, get_file_processing_status, save_subtitles, get_subtitles, list_uploaded_files
from src.whisperx_integration import run_whisperx_on_file

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="Subtitle Sync Backend",
    description="Backend API for subtitle synchronization using WhisperX.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Upload & Process", "description": "Upload files and process subtitles."},
        {"name": "Status", "description": "Query processing jobs."},
        {"name": "Subtitles", "description": "Get synchronized subtitles."},
        {"name": "Files", "description": "List/download available files."},
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploaded", StaticFiles(directory=UPLOAD_DIR), name="uploaded")

# PUBLIC_INTERFACE
@app.get("/")
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}

# PUBLIC_INTERFACE
@app.post("/upload", response_model=FileUploadResponse, tags=["Upload & Process"], summary="Upload an audio/video file")
async def upload_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """
    Upload an audio or video file for subtitle synchronization.
    Returns a task ID to track status and retrieve results.
    - **file**: Audio or video file to process.
    """
    task_id = str(uuid.uuid4())
    saved_path = os.path.join(UPLOAD_DIR, f"{task_id}_{file.filename}")
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    save_file_processing_status(task_id, status="uploaded", error=None, progress=0)
    # Start processing as a background task so REST call returns immediately
    background_tasks.add_task(_process_file, saved_path, task_id)
    return {"task_id": task_id}

def _process_file(filepath: str, task_id: str):
    """
    The actual file processing logic run in the background.
    Invokes WhisperX, updates DB, etc.
    """
    try:
        save_file_processing_status(task_id, status="processing", error=None, progress=20)
        # Simulated processing time, progress increments can be refined
        subtitles = run_whisperx_on_file(filepath)
        save_subtitles(task_id, subtitles)
        save_file_processing_status(task_id, status="completed", error=None, progress=100)
    except Exception as ex:
        save_file_processing_status(task_id, status="error", error=str(ex), progress=None)

# PUBLIC_INTERFACE
@app.get("/status/{task_id}", response_model=StatusResponse, tags=["Status"], summary="Get processing status for a file")
async def get_status(task_id: str):
    """
    Get the processing status of an uploaded file.
    Returns task status, error (if any), and progress.
    """
    rec = get_file_processing_status(task_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Task ID not found")
    return {
        "task_id": task_id,
        "status": rec.get("status", "unknown"),
        "error": rec.get("error"),
        "progress": rec.get("progress"),
    }

# PUBLIC_INTERFACE
@app.get("/subtitles/{task_id}", response_model=SubtitlesResponse, tags=["Subtitles"], summary="Get synchronized subtitles for a task")
async def get_subtitles_endpoint(task_id: str):
    """
    Retrieve synchronized subtitles for a file after processing.
    Returns a list of subtitle lines.
    """
    subtitle_list = get_subtitles(task_id)
    if not subtitle_list:
        raise HTTPException(status_code=404, detail="No subtitles found for task")
    lines = [SubtitleLine(**s) for s in subtitle_list]
    return {"task_id": task_id, "subtitles": lines}

# PUBLIC_INTERFACE
@app.get("/files", response_model=ListFilesResponse, tags=["Files"], summary="List uploaded files")
async def list_files():
    """
    List all uploaded files currently in the system.
    """
    files = list_uploaded_files(UPLOAD_DIR)
    return {"files": files}

# PUBLIC_INTERFACE
@app.get("/files/{filename}", response_class=FileResponse, tags=["Files"], summary="Download an uploaded file")
async def download_file(filename: str):
    """
    Download an uploaded media file by filename.
    """
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/octet-stream", filename=filename)
