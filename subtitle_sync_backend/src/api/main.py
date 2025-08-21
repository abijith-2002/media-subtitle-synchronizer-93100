import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette import status

from .settings import Settings, get_settings
from .db import get_engine, get_session_maker, init_db
from .models import MediaFile, ProcessingStatusEnum
from .schemas import UploadResponse, StatusResponse, FileItem, FilesListResponse
from .services.processing import process_media_with_whisperx

# Initialize application with metadata and OpenAPI tags
app = FastAPI(
    title="Subtitle Sync Backend API",
    version="1.0.0",
    description=(
        "Backend API running WhisperX for media subtitle synchronization.\n\n"
        "Features:\n"
        "- Upload audio/video files\n"
        "- Process via WhisperX (async background task)\n"
        "- Check processing status\n"
        "- Download generated subtitles\n"
        "- List uploaded files\n\n"
        "Theme support: pass query parameter 'theme=dark|light' or 'X-Theme' header to toggle the docs theme hint in the OpenAPI schema.\n"
    ),
    openapi_tags=[
        {"name": "health", "description": "Health and diagnostics"},
        {"name": "files", "description": "File management (upload/list)"},
        {"name": "processing", "description": "Processing status"},
        {"name": "subtitles", "description": "Subtitle retrieval and download"},
        {"name": "websocket", "description": "WebSocket usage help (if applicable in future)"},
    ],
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this via env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure required directories exist based on env
settings: Settings = get_settings()
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.SUBTITLE_DIR).mkdir(parents=True, exist_ok=True)

# Database initialization
engine = get_engine(settings)
SessionLocal = get_session_maker(engine)
init_db(engine)


# PUBLIC_INTERFACE
@app.get("/", tags=["health"], summary="Health Check", description="Simple health check endpoint to verify service availability.")
def health_check():
    """This endpoint returns a simple message indicating that the service is healthy."""
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.post(
    "/upload",
    tags=["files"],
    summary="Upload a media file",
    description=(
        "Upload an audio/video file to be processed. The server stores the file, creates a database record, "
        "and triggers a background task to run WhisperX and generate synchronized subtitles."
    ),
    status_code=status.HTTP_202_ACCEPTED,
    response_model=UploadResponse,
)
async def upload_media(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Audio/Video media file to upload for subtitle synchronization."),
    theme: Optional[str] = Query(None, description="Theme preference for docs UI hint (dark|light)."),
    x_theme: Optional[str] = Header(None, convert_underscores=False, description="Theme preference header (dark|light)."),
):
    """
    Accepts an uploaded file, stores it on disk, creates a DB entry with PENDING status,
    and starts a background task to process with WhisperX.
    Returns an identifier for querying status and subtitles.
    """
    chosen_theme = (theme or x_theme or "").lower() or "light"
    if chosen_theme not in ("dark", "light"):
        chosen_theme = "light"

    # Validate file content type quickly (basic)
    filename = file.filename or "uploaded_media"
    ext = Path(filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension '{ext}'. Allowed: {settings.ALLOWED_EXTENSIONS}")

    media_id = str(uuid.uuid4())
    media_filename = f"{media_id}{ext}"
    media_path = Path(settings.UPLOAD_DIR) / media_filename

    # Save uploaded file to disk
    try:
        with media_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store uploaded file: {e}") from e
    finally:
        await file.close()

    # Create DB record
    db = SessionLocal()
    try:
        media = MediaFile(
            id=media_id,
            original_filename=filename,
            stored_path=str(media_path),
            status=ProcessingStatusEnum.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            subtitle_path=None,
            error_message=None,
        )
        db.add(media)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}") from e
    finally:
        db.close()

    # Kick off background processing
    background_tasks.add_task(
        process_media_with_whisperx,
        media_id=media_id,
        media_path=str(media_path),
        subtitle_dir=settings.SUBTITLE_DIR,
        db_maker=SessionLocal,
        settings=settings,
    )

    return UploadResponse(
        id=media_id,
        filename=filename,
        status="accepted",
        theme=chosen_theme,
        message="Upload accepted. Processing started.",
    )


# PUBLIC_INTERFACE
@app.get(
    "/status",
    tags=["processing"],
    summary="Get processing status",
    description="Query the processing status for an uploaded media by its id.",
    response_model=StatusResponse,
)
def get_status(
    id: str = Query(..., description="The id returned by the upload endpoint."),
    theme: Optional[str] = Query(None, description="Theme preference for docs UI hint (dark|light)."),
    x_theme: Optional[str] = Header(None, convert_underscores=False, description="Theme preference header (dark|light)."),
):
    """Returns current processing status, any error message, and timestamp info for a given media id."""
    chosen_theme = (theme or x_theme or "").lower() or "light"
    if chosen_theme not in ("dark", "light"):
        chosen_theme = "light"

    db = SessionLocal()
    try:
        media = db.get(MediaFile, id)
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")

        return StatusResponse(
            id=media.id,
            filename=media.original_filename,
            status=media.status.value,
            created_at=media.created_at,
            updated_at=media.updated_at,
            error_message=media.error_message,
            theme=chosen_theme,
        )
    finally:
        db.close()


# PUBLIC_INTERFACE
@app.get(
    "/subtitles",
    tags=["subtitles"],
    summary="Get or download subtitles",
    description=(
        "Retrieve the generated subtitles for a processed media. If 'download=true' is provided, "
        "the response will be a file download. Otherwise, returns the subtitle file content."
    ),
)
def get_subtitles(
    id: str = Query(..., description="The id returned by the upload endpoint."),
    download: bool = Query(False, description="Set true to download the subtitle file."),
):
    """
    Returns subtitle file content or triggers a file download for the generated subtitles.
    """
    db = SessionLocal()
    try:
        media = db.get(MediaFile, id)
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")

        if media.status != ProcessingStatusEnum.COMPLETED or not media.subtitle_path:
            raise HTTPException(status_code=400, detail="Subtitles not available yet")

        sub_path = Path(media.subtitle_path)
        if not sub_path.exists():
            raise HTTPException(status_code=404, detail="Subtitle file not found on server")

        if download:
            return FileResponse(
                path=str(sub_path),
                filename=sub_path.name,
                media_type="text/plain",
            )

        # Return content inline
        try:
            content = sub_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback to binary for odd encodings
            return FileResponse(path=str(sub_path), media_type="application/octet-stream", filename=sub_path.name)

        return Response(content=content, media_type="text/plain")
    finally:
        db.close()


# PUBLIC_INTERFACE
@app.get(
    "/files",
    tags=["files"],
    summary="List uploaded files",
    description="Lists uploaded files with their current processing status.",
    response_model=FilesListResponse,
)
def list_files():
    """Lists files stored in the system and their statuses."""
    db = SessionLocal()
    try:
        items: List[FileItem] = []
        for media in db.query(MediaFile).order_by(MediaFile.created_at.desc()).all():
            items.append(
                FileItem(
                    id=media.id,
                    filename=media.original_filename,
                    status=media.status.value,
                    created_at=media.created_at,
                    updated_at=media.updated_at,
                )
            )
        return FilesListResponse(files=items, total=len(items))
    finally:
        db.close()


# PUBLIC_INTERFACE
@app.get(
    "/websocket-docs",
    tags=["websocket"],
    summary="WebSocket usage help",
    description=(
        "Note: Real-time processing updates could be delivered via WebSocket in future enhancement. "
        "Clients would connect to a WebSocket endpoint (e.g., /ws) to receive live status. "
        "This endpoint documents potential future usage."
    ),
)
def websocket_usage_help():
    """Provides informative notes about future WebSocket usage for live updates (not currently implemented)."""
    return {"message": "WebSocket endpoint not implemented yet. Future endpoint could be /ws to stream live status updates."}


# Static mounting (optional for serving generated files via static URL if needed)
app.mount("/static", StaticFiles(directory=settings.SUBTITLE_DIR), name="static")
