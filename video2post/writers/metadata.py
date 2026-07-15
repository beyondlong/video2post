import json
from datetime import datetime
from pathlib import Path

from video2post.models import ErrorDetails, TaskMetadata, TaskStatus


def write_metadata(metadata: TaskMetadata) -> Path:
    metadata.task_dir.mkdir(parents=True, exist_ok=True)
    metadata.updated_at = datetime.now()
    target = metadata.task_dir / "meta.json"
    target.write_text(
        json.dumps(metadata.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return target


def read_metadata(path: Path | str) -> TaskMetadata:
    metadata_path = Path(path)
    raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    return TaskMetadata.model_validate(raw)


def update_status(
    path: Path | str,
    status: TaskStatus,
    *,
    error_stage: str | None = None,
    error_message: str | None = None,
    retryable: bool = False,
    error_code: "ErrorCode | None" = None,
    fix_suggestions: list[str] | None = None,
) -> TaskMetadata:
    from video2post.models import ErrorCode

    metadata = read_metadata(path)
    metadata.status = status
    metadata.updated_at = datetime.now()
    if error_stage or error_message:
        metadata.error = ErrorDetails(
            stage=error_stage or status.value,
            message=error_message or "",
            retryable=retryable,
            error_code=error_code or ErrorCode.UNKNOWN,
            fix_suggestions=fix_suggestions or [],
        )
        if status == TaskStatus.FAILED:
            metadata.retry_count += 1
    elif status != TaskStatus.FAILED:
        metadata.error = None
    write_metadata(metadata)
    return metadata
