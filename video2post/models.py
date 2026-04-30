from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    CREATED = "created"
    METADATA_FETCHED = "metadata_fetched"
    AUDIO_DOWNLOADED = "audio_downloaded"
    AUDIO_NORMALIZED = "audio_normalized"
    TRANSCRIBED = "transcribed"
    TRANSLATED_OR_CLEANED = "translated_or_cleaned"
    NOTES_GENERATED = "notes_generated"
    ARTICLE_GENERATED = "article_generated"
    SCRIPT_GENERATED = "script_generated"
    TITLES_GENERATED = "titles_generated"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoMetadata(BaseModel):
    title: str | None = None
    author: str | None = None
    duration_seconds: int | None = None
    published_at: str | None = None


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    language: str | None = None


class ErrorDetails(BaseModel):
    stage: str
    message: str
    retryable: bool = False


class TaskMetadata(BaseModel):
    source_url: str
    platform: str
    task_dir: Path
    status: TaskStatus = TaskStatus.CREATED
    video: VideoMetadata = Field(default_factory=VideoMetadata)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    asr_model: str | None = None
    llm_model: str | None = None
    error: ErrorDetails | None = None
