import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column, relationship, Session
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Application config defaults (use env to override)
APP_TITLE = os.getenv("APP_TITLE", "Subtitle Sync Backend")
APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "API to upload media, run WhisperX to sync subtitles, and manage downloads.")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()]
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
SUBTITLE_DIR = Path(os.getenv("SUBTITLE_DIR", "data/subtitles"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local.db")  # Use PostgreSQL in production via env
# Example PostgreSQL: postgresql+psycopg2://user:password@host:port/dbname

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SUBTITLE_DIR.mkdir(parents=True, exist_ok=True)


# SQLAlchemy setup
class Base(DeclarativeBase):
    pass


class ProcessingStatusEnum(str):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class UserPreference(Base):
    __tablename__ = "user_preferences"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    theme: Mapped[str] = mapped_column(String(16), default="light")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MediaFile(Base):
    __tablename__ = "media_files"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), index=True, unique=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128))
    file_path: Mapped[str] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # relationships
    processing: Mapped["ProcessingJob"] = relationship(back_populates="media_file", uselist=False)
    subtitles: Mapped[List["Subtitle"]] = relationship(back_populates="media_file")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), index=True, unique=True)
    media_file_id: Mapped[int] = mapped_column(ForeignKey("media_files.id"))
    status: Mapped[str] = mapped_column(String(16), default=ProcessingStatusEnum.PENDING)
    status_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    media_file: Mapped[MediaFile] = relationship(back_populates="processing")


class Subtitle(Base):
    __tablename__ = "subtitles"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    media_file_id: Mapped[int] = mapped_column(ForeignKey("media_files.id"))
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    # Store both file reference and raw content (SRT/ASS)
    subtitle_format: Mapped[str] = mapped_column(String(16), default="srt")
    content: Mapped[str] = mapped_column(Text)  # textual content for quick API retrieval
    file_path: Mapped[str] = mapped_column(Text)  # saved file on disk
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    media_file: Mapped[MediaFile] = relationship(back_populates="subtitles")


# Create engine and session
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

# Initialize DB schema
Base.metadata.create_all(bind=engine)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic models for API
class UploadResponse(BaseModel):
    job_id: str = Field(..., description="Unique job identifier")
    filename: str = Field(..., description="Uploaded file name")
    status: str = Field(..., description="Initial processing status")


class StatusResponse(BaseModel):
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Processing status")
    message: Optional[str] = Field(None, description="Optional status message")
    filename: Optional[str] = Field(None, description="Original filename")
    uploaded_at: Optional[datetime] = Field(None, description="Upload timestamp")


class SubtitleItem(BaseModel):
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Subtitle text")


class SubtitlesResponse(BaseModel):
    job_id: str = Field(..., description="Job identifier")
    format: str = Field(..., description="Subtitle format (e.g., srt)")
    items: List[SubtitleItem] = Field(..., description="List of subtitle items")


class FilesResponse(BaseModel):
    job_id: str = Field(..., description="Job identifier")
    original_filename: str = Field(..., description="Original uploaded file name")
    original_download_url: str = Field(..., description="URL to download original file")
    subtitle_download_url: Optional[str] = Field(None, description="URL to download generated subtitles")


class ThemeRequest(BaseModel):
    user_id: str = Field(..., description="User ID for preference storage")
    theme: str = Field(..., description="Theme preference: light or dark")


class ThemeResponse(BaseModel):
    user_id: str = Field(..., description="User ID")
    theme: str = Field(..., description="Current theme preference")


# FastAPI app with OpenAPI metadata and tags
openapi_tags = [
    {"name": "Health", "description": "Health check and service info"},
    {"name": "Upload", "description": "Upload and process media files"},
    {"name": "Status", "description": "Check processing status"},
    {"name": "Subtitles", "description": "Retrieve generated subtitles"},
    {"name": "Files", "description": "Download original or subtitle files"},
    {"name": "Preferences", "description": "User theme preference"},
]

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper: save UploadFile to disk safely
def _save_upload(file: UploadFile, dest_folder: Path, name_prefix: str) -> Path:
    dest_folder.mkdir(parents=True, exist_ok=True)
    safe_name = f"{name_prefix}_{Path(file.filename).name}"
    dest = dest_folder / safe_name
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    return dest


# Placeholder WhisperX processing function
def run_whisperx_generate_subtitles(media_path: Path) -> List[SubtitleItem]:
    """
    In a production environment, this would:
    - Load WhisperX model
    - Transcribe audio/video
    - Align words with timestamps
    - Aggregate into subtitle lines
    Here we return mocked subtitles for demonstration.
    """
    # Mocked simple subtitles
    return [
        SubtitleItem(start=0.0, end=2.5, text="Hello, welcome to the demo."),
        SubtitleItem(start=2.6, end=5.0, text="This is a placeholder WhisperX output."),
        SubtitleItem(start=5.1, end=7.5, text="Replace with real model integration."),
    ]


def _serialize_srt(items: List[SubtitleItem]) -> str:
    def fmt_time(sec: float) -> str:
        ms = int((sec - int(sec)) * 1000)
        s = int(sec) % 60
        m = (int(sec) // 60) % 60
        h = int(sec) // 3600
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    for idx, it in enumerate(items, start=1):
        lines.append(str(idx))
        lines.append(f"{fmt_time(it.start)} --> {fmt_time(it.end)}")
        lines.append(it.text)
        lines.append("")  # blank line
    return "\n".join(lines)


def _create_subtitle_file(job_id: str, items: List[SubtitleItem], fmt: str = "srt") -> Path:
    SUBTITLE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{job_id}.{fmt}"
    path = SUBTITLE_DIR / filename
    if fmt.lower() == "srt":
        content = _serialize_srt(items)
    else:
        # Default to srt content; expand for other formats if needed
        content = _serialize_srt(items)
    path.write_text(content, encoding="utf-8")
    return path


def _update_status(db: Session, job_id: str, status: str, message: Optional[str] = None) -> None:
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
    if job:
        job.status = status
        job.status_message = message
        job.updated_at = datetime.utcnow()
        db.add(job)
        db.commit()


def _background_process(job_id: str, media_path: Path, db_url: str):
    """
    Background processing wrapper to avoid passing active session across threads.
    """
    local_engine = create_engine(db_url, echo=False, future=True)
    LocalSession = sessionmaker(bind=local_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    db = LocalSession()
    try:
        _update_status(db, job_id, ProcessingStatusEnum.PROCESSING, "Started processing with WhisperX")
        # Run WhisperX (placeholder)
        items = run_whisperx_generate_subtitles(media_path)
        # Save subtitle file
        subtitle_path = _create_subtitle_file(job_id, items, fmt="srt")
        # Persist subtitle record
        media = db.query(MediaFile).filter(MediaFile.job_id == job_id).first()
        if not media:
            _update_status(db, job_id, ProcessingStatusEnum.FAILED, "Media record not found")
            return

        subtitle_text = subtitle_path.read_text(encoding="utf-8")
        sub = Subtitle(
            media_file_id=media.id,
            job_id=job_id,
            subtitle_format="srt",
            content=subtitle_text,
            file_path=str(subtitle_path),
        )
        db.add(sub)
        _update_status(db, job_id, ProcessingStatusEnum.SUCCESS, "Subtitles generated successfully")
        db.commit()
    except Exception as ex:
        _update_status(db, job_id, ProcessingStatusEnum.FAILED, f"Error: {ex}")
    finally:
        db.close()


# PUBLIC_INTERFACE
@app.get("/", tags=["Health"], summary="Health Check")
def health_check():
    """Health check endpoint that verifies the service is running."""
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.post("/upload", response_model=UploadResponse, status_code=HTTP_201_CREATED, tags=["Upload"], summary="Upload a media file", description="Upload an audio/video file for subtitle synchronization. Returns a job_id to check status and retrieve results later.")
async def upload_media(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Validate content type roughly
    if not file.content_type or not any(t in file.content_type for t in ["audio", "video", "octet-stream"]):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    job_id = str(uuid.uuid4())
    # Persist media file
    saved_path = _save_upload(file, UPLOAD_DIR, name_prefix=job_id)

    media = MediaFile(
        job_id=job_id,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        file_path=str(saved_path),
    )
    db.add(media)
    db.commit()
    db.refresh(media)

    job = ProcessingJob(
        job_id=job_id,
        media_file_id=media.id,
        status=ProcessingStatusEnum.PENDING,
        status_message="Queued for processing",
    )
    db.add(job)
    db.commit()

    # Launch background processing
    background_tasks.add_task(_background_process, job_id, saved_path, DATABASE_URL)

    return UploadResponse(job_id=job_id, filename=file.filename, status=job.status)


# PUBLIC_INTERFACE
@app.get("/status/{job_id}", response_model=StatusResponse, tags=["Status"], summary="Check processing status", description="Get the current processing status for a given job_id.")
def get_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Job not found")
    media = db.query(MediaFile).filter(MediaFile.id == job.media_file_id).first()
    return StatusResponse(
        job_id=job.job_id,
        status=job.status,
        message=job.status_message,
        filename=media.filename if media else None,
        uploaded_at=media.uploaded_at if media else None,
    )


# PUBLIC_INTERFACE
@app.get("/subtitles/{job_id}", response_model=SubtitlesResponse, tags=["Subtitles"], summary="Retrieve generated subtitles", description="Retrieve synchronized subtitles for a job_id. Returns structured items in JSON.")
def get_subtitles(job_id: str, db: Session = Depends(get_db)):
    sub = db.query(Subtitle).filter(Subtitle.job_id == job_id).order_by(Subtitle.created_at.desc()).first()
    if not sub:
        # Check status to give a better error
        job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
        if job and job.status in (ProcessingStatusEnum.PENDING, ProcessingStatusEnum.PROCESSING):
            raise HTTPException(status_code=202, detail=f"Subtitles not ready. Status: {job.status}")
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Subtitles not found")

    # Parse SRT content to structured items (simple parser for the mocked output)
    items: List[SubtitleItem] = []
    blocks = [b for b in sub.content.split("\n\n") if b.strip()]
    for block in blocks:
        lines = [l for l in block.splitlines() if l.strip()]
        if len(lines) >= 3:
            # lines[0]: index, lines[1]: time range, lines[2..]: text
            time_line = lines[1]
            try:
                start_str, end_str = time_line.split("-->")
                start_str, end_str = start_str.strip(), end_str.strip()
                def parse_time(s: str) -> float:
                    hms, ms = s.split(",")
                    h, m, sec = hms.split(":")
                    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000.0
                start = parse_time(start_str)
                end = parse_time(end_str)
                text = " ".join(lines[2:])
                items.append(SubtitleItem(start=start, end=end, text=text))
            except Exception:
                # skip malformed blocks
                continue

    return SubtitlesResponse(job_id=job_id, format=sub.subtitle_format, items=items)


# PUBLIC_INTERFACE
@app.get("/files/{job_id}/original", tags=["Files"], summary="Download original file", description="Download the originally uploaded media file for the given job_id.")
def download_original(job_id: str, db: Session = Depends(get_db)):
    media = db.query(MediaFile).filter(MediaFile.job_id == job_id).first()
    if not media:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Media not found")
    path = Path(media.file_path)
    if not path.exists():
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="File not found on server")
    return FileResponse(path, filename=Path(media.filename).name, media_type=media.content_type)


# PUBLIC_INTERFACE
@app.get("/files/{job_id}/subtitle", tags=["Files"], summary="Download subtitle file", description="Download the generated subtitle file (SRT) for the given job_id.")
def download_subtitle(job_id: str, db: Session = Depends(get_db)):
    sub = db.query(Subtitle).filter(Subtitle.job_id == job_id).order_by(Subtitle.created_at.desc()).first()
    if not sub:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Subtitle not found")
    path = Path(sub.file_path)
    if not path.exists():
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Subtitle file not found on server")
    media_type = "application/x-subrip" if sub.subtitle_format.lower() == "srt" else "text/plain"
    return FileResponse(path, filename=path.name, media_type=media_type)


# PUBLIC_INTERFACE
@app.get("/files/{job_id}", response_model=FilesResponse, tags=["Files"], summary="Get file links", description="Get URLs for downloading original and subtitle files for the given job_id.")
def get_file_links(job_id: str, db: Session = Depends(get_db)):
    media = db.query(MediaFile).filter(MediaFile.job_id == job_id).first()
    if not media:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Media not found")
    # Since we don't know the public base URL at runtime, return relative URLs the frontend can resolve.
    original_url = f"/files/{job_id}/original"
    subtitle = db.query(Subtitle).filter(Subtitle.job_id == job_id).order_by(Subtitle.created_at.desc()).first()
    subtitle_url = f"/files/{job_id}/subtitle" if subtitle else None
    return FilesResponse(
        job_id=job_id,
        original_filename=media.filename,
        original_download_url=original_url,
        subtitle_download_url=subtitle_url,
    )


# PUBLIC_INTERFACE
@app.post("/preferences/theme", response_model=ThemeResponse, tags=["Preferences"], summary="Set theme preference", description="Set the user's theme preference (light or dark).")
def set_theme(req: ThemeRequest, db: Session = Depends(get_db)):
    theme = req.theme.lower()
    if theme not in {"light", "dark"}:
        raise HTTPException(status_code=400, detail="Theme must be 'light' or 'dark'")
    pref = db.query(UserPreference).filter(UserPreference.user_id == req.user_id).first()
    if pref:
        pref.theme = theme
        pref.updated_at = datetime.utcnow()
        db.add(pref)
    else:
        pref = UserPreference(user_id=req.user_id, theme=theme)
        db.add(pref)
    db.commit()
    return ThemeResponse(user_id=req.user_id, theme=pref.theme)


# PUBLIC_INTERFACE
@app.get("/preferences/theme", response_model=ThemeResponse, tags=["Preferences"], summary="Get theme preference", description="Retrieve the user's theme preference.")
def get_theme(user_id: str = Query(..., description="User ID"), db: Session = Depends(get_db)):
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if not pref:
        # default if none stored
        return ThemeResponse(user_id=user_id, theme="light")
    return ThemeResponse(user_id=user_id, theme=pref.theme)


# PUBLIC_INTERFACE
@app.get("/docs/websocket", tags=["Health"], summary="WebSocket usage info", description="Note: This service currently does not expose a WebSocket endpoint. Real-time updates can be implemented in future versions.")
def websocket_info():
    return {"message": "No WebSocket endpoints. Poll /status/{job_id} for updates."}
