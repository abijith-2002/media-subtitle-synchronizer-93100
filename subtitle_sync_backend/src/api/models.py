# src/api/models.py

from pydantic import BaseModel, Field
from typing import Optional, List

# PUBLIC_INTERFACE
class FileUploadResponse(BaseModel):
    """Response model for file upload."""
    task_id: str = Field(..., description="Unique task identifier for the uploaded file.")

# PUBLIC_INTERFACE
class StatusResponse(BaseModel):
    """Response model for status of processing."""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Current processing status")
    error: Optional[str] = Field(None, description="Error message, if any")
    progress: Optional[int] = Field(None, description="Progress (percent, optional)")

# PUBLIC_INTERFACE
class SubtitleLine(BaseModel):
    """A single line of subtitle, with start/end and text."""
    start: float = Field(..., description="Start time (sec)")
    end: float = Field(..., description="End time (sec)")
    text: str = Field(..., description="Subtitle text")

# PUBLIC_INTERFACE
class SubtitlesResponse(BaseModel):
    """Response model for returning subtitles."""
    task_id: str = Field(..., description="Task identifier")
    subtitles: List[SubtitleLine] = Field(..., description="List of subtitle lines.")

# PUBLIC_INTERFACE
class ListFilesResponse(BaseModel):
    """Response model for available files."""
    files: List[str] = Field(..., description="List of filenames uploaded/available.")

