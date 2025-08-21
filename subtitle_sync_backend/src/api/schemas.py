from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# PUBLIC_INTERFACE
class UploadResponse(BaseModel):
    """Response model for upload endpoint."""
    id: str = Field(..., description="Unique media id used for status and subtitle retrieval.")
    filename: str = Field(..., description="Original uploaded file name.")
    status: str = Field(..., description="Status of the request (e.g. accepted).")
    message: str = Field(..., description="Informational message.")
    theme: str = Field(..., description="Theme preference (light|dark) echoed back.")


# PUBLIC_INTERFACE
class StatusResponse(BaseModel):
    """Processing status for a given media id."""
    id: str = Field(..., description="Media id.")
    filename: str = Field(..., description="Original uploaded file name.")
    status: str = Field(..., description="Current processing status (pending|processing|completed|failed).")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")
    error_message: Optional[str] = Field(None, description="Error message if failed.")
    theme: Optional[str] = Field(None, description="Theme preference echoed back (if provided).")


# PUBLIC_INTERFACE
class FileItem(BaseModel):
    """List item for uploaded files."""
    id: str = Field(..., description="Media id.")
    filename: str = Field(..., description="Original file name.")
    status: str = Field(..., description="Processing status.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


# PUBLIC_INTERFACE
class FilesListResponse(BaseModel):
    """Response model for listing files."""
    files: List[FileItem] = Field(..., description="List of uploaded files.")
    total: int = Field(..., description="Total number of files.")
