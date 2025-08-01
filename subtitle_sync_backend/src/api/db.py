# src/api/db.py
"""Database access layer for subtitle_sync_backend. Replace with actual implementation."""

import os
from typing import Dict, Optional, List

# Simulate an in-memory 'database' for demo purposes
IN_MEMORY_DB: Dict[str, dict] = {}  # Maps task_id to status/subtitle info

# PUBLIC_INTERFACE
def save_file_processing_status(task_id: str, status: str, error: Optional[str] = None, progress: Optional[int] = None):
    """Update or insert a processing status entry."""
    if task_id not in IN_MEMORY_DB:
        IN_MEMORY_DB[task_id] = {}
    IN_MEMORY_DB[task_id]['status'] = status
    IN_MEMORY_DB[task_id]['error'] = error
    IN_MEMORY_DB[task_id]['progress'] = progress

# PUBLIC_INTERFACE
def get_file_processing_status(task_id: str):
    """Get the processing status for a specific file."""
    return IN_MEMORY_DB.get(task_id, None)

# PUBLIC_INTERFACE
def save_subtitles(task_id: str, subtitles: List[dict]):
    """Save generated subtitles for a task_id."""
    if task_id not in IN_MEMORY_DB:
        IN_MEMORY_DB[task_id] = {}
    IN_MEMORY_DB[task_id]['subtitles'] = subtitles

# PUBLIC_INTERFACE
def get_subtitles(task_id: str) -> Optional[List[dict]]:
    """Get subtitles for a given task_id."""
    item = IN_MEMORY_DB.get(task_id)
    if item and 'subtitles' in item:
        return item['subtitles']
    return None

# PUBLIC_INTERFACE
def list_uploaded_files(upload_dir: str) -> List[str]:
    """List uploaded files in the upload directory."""
    if not os.path.exists(upload_dir):
        return []
    return [f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f))]

