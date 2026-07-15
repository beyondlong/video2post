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
    COVER_GENERATED = "cover_generated"
    X_ARTICLE_GENERATED = "x_article_generated"
    X_THREAD_GENERATED = "x_thread_generated"
    X_TITLES_GENERATED = "x_titles_generated"
    ARTICLE_GENERATED = "article_generated"
    SCRIPT_GENERATED = "script_generated"
    TITLES_GENERATED = "titles_generated"
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorCode(StrEnum):
    UNKNOWN = "unknown"
    DOWNLOAD_COOKIE_AUTH = "download_cookie_auth"
    DOWNLOAD_JS_CHALLENGE = "download_js_challenge"
    DOWNLOAD_VIDEO_UNAVAILABLE = "download_video_unavailable"
    DOWNLOAD_NETWORK = "download_network"
    FFMPEG_NOT_FOUND = "ffmpeg_not_found"
    FFMPEG_CONVERSION_FAILED = "ffmpeg_conversion_failed"
    ASR_MODEL_NOT_INSTALLED = "asr_model_not_installed"
    ASR_TRANSCRIPTION_FAILED = "asr_transcription_failed"
    ASR_QUALITY_CHECK_FAILED = "asr_quality_check_failed"
    LLM_AUTH_FAILED = "llm_auth_failed"
    LLM_MISSING_CONFIG = "llm_missing_config"
    LLM_RATE_LIMIT = "llm_rate_limit"
    LLM_TIMEOUT = "llm_timeout"
    LLM_CONTENT_FILTERED = "llm_content_filtered"
    LLM_PROVIDER_ERROR = "llm_provider_error"
    LLM_REFUSAL = "llm_refusal"
    FILE_NOT_FOUND = "file_not_found"
    INVALID_INPUT = "invalid_input"


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
    error_code: ErrorCode = ErrorCode.UNKNOWN
    fix_suggestions: list[str] = Field(default_factory=list)


class TaskMetadata(BaseModel):
    source_url: str
    platform: str
    task_dir: Path
    status: TaskStatus = TaskStatus.CREATED
    video: VideoMetadata = Field(default_factory=VideoMetadata)
    source_language: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    asr_model: str | None = None
    llm_model: str | None = None
    error: ErrorDetails | None = None
    retry_count: int = 0
