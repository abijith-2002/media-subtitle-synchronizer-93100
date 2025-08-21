import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ProcessingStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MediaFile(Base):
    """Media file record with processing status and subtitle path."""
    __tablename__ = "media_files"

    id = Column(String(64), primary_key=True, index=True)
    original_filename = Column(String(512), nullable=False)
    stored_path = Column(String(1024), nullable=False)
    subtitle_path = Column(String(1024), nullable=True)

    status = Column(Enum(ProcessingStatusEnum), default=ProcessingStatusEnum.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
