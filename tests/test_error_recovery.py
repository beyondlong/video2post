"""Tests for enhanced error recovery: task status, retry tracking, structured errors."""

import json

from typer.testing import CliRunner

from video2post.cli import app
from video2post.models import ErrorCode, ErrorDetails, TaskMetadata, TaskStatus, VideoMetadata
from video2post.writers.metadata import read_metadata, update_status, write_metadata

runner = CliRunner()


def test_update_status_records_error_code_and_suggestions(tmp_path):
    metadata = TaskMetadata(
        source_url="https://youtu.be/test",
        platform="youtube",
        task_dir=tmp_path,
        status=TaskStatus.AUDIO_DOWNLOADED,
        video=VideoMetadata(title="Test"),
    )
    write_metadata(metadata)

    updated = update_status(
        tmp_path / "meta.json",
        TaskStatus.FAILED,
        error_stage="audio_download",
        error_message="cookie auth required",
        retryable=True,
        error_code=ErrorCode.DOWNLOAD_COOKIE_AUTH,
        fix_suggestions=["Install node", "Add cookies config"],
    )

    assert updated.error.error_code == ErrorCode.DOWNLOAD_COOKIE_AUTH
    assert updated.error.fix_suggestions == ["Install node", "Add cookies config"]
    assert updated.error.retryable is True
    assert updated.retry_count == 1


def test_update_status_increments_retry_count_on_repeated_failures(tmp_path):
    metadata = TaskMetadata(
        source_url="https://youtu.be/test",
        platform="youtube",
        task_dir=tmp_path,
        status=TaskStatus.CREATED,
        video=VideoMetadata(title="Test"),
    )
    write_metadata(metadata)

    update_status(
        tmp_path / "meta.json",
        TaskStatus.FAILED,
        error_stage="download",
        error_message="first failure",
    )
    update_status(
        tmp_path / "meta.json",
        TaskStatus.FAILED,
        error_stage="download",
        error_message="second failure",
    )

    loaded = read_metadata(tmp_path / "meta.json")
    assert loaded.retry_count == 2


def test_update_status_clears_error_on_success(tmp_path):
    metadata = TaskMetadata(
        source_url="https://youtu.be/test",
        platform="youtube",
        task_dir=tmp_path,
        status=TaskStatus.FAILED,
        video=VideoMetadata(title="Test"),
        retry_count=2,
        error=ErrorDetails(
            stage="download",
            message="old error",
            error_code=ErrorCode.DOWNLOAD_COOKIE_AUTH,
        ),
    )
    write_metadata(metadata)

    updated = update_status(
        tmp_path / "meta.json",
        TaskStatus.AUDIO_NORMALIZED,
    )

    assert updated.error is None
    assert updated.retry_count == 2


def test_error_details_defaults_for_backward_compatibility(tmp_path):
    metadata = TaskMetadata(
        source_url="https://youtu.be/test",
        platform="youtube",
        task_dir=tmp_path,
        status=TaskStatus.FAILED,
        video=VideoMetadata(title="Test"),
        error=ErrorDetails(stage="download", message="old-style error"),
    )
    write_metadata(metadata)

    loaded = read_metadata(tmp_path / "meta.json")
    assert loaded.error.error_code == ErrorCode.UNKNOWN
    assert loaded.error.fix_suggestions == []
    assert loaded.error.retryable is False


def test_task_status_command_shows_healthy_task(tmp_path):
    _write_task_metadata(tmp_path, status=TaskStatus.TRANSCRIBED)
    (tmp_path / "audio.wav").write_bytes(b"audio")

    result = runner.invoke(app, ["task", "status", str(tmp_path)])

    assert result.exit_code == 0
    assert "Status: transcribed" in result.output
    assert "Platform: youtube" in result.output
    assert "audio" in result.output


def test_task_status_command_shows_error_diagnostics(tmp_path):
    metadata = TaskMetadata(
        source_url="https://youtu.be/test",
        platform="youtube",
        task_dir=tmp_path,
        status=TaskStatus.FAILED,
        video=VideoMetadata(title="Test Video"),
        retry_count=2,
        error=ErrorDetails(
            stage="audio_download",
            message="Sign in to confirm you're not a bot",
            retryable=True,
            error_code=ErrorCode.DOWNLOAD_COOKIE_AUTH,
            fix_suggestions=["Install node", "Add cookies config"],
        ),
    )
    write_metadata(metadata)

    result = runner.invoke(app, ["task", "status", str(tmp_path)])

    assert result.exit_code == 0
    assert "Status: failed" in result.output
    assert "Retry count: 2" in result.output
    assert "browser cookies" in result.output
    assert "Install node" in result.output
    assert "retryable" in result.output.lower()


def test_task_status_command_handles_missing_metadata(tmp_path):
    result = runner.invoke(app, ["task", "status", str(tmp_path)])

    assert result.exit_code == 1
    assert "Cannot read task metadata" in result.output


def test_task_help_exposes_status_subcommand():
    result = runner.invoke(app, ["task", "--help"])

    assert result.exit_code == 0
    assert "status" in result.output


def test_task_list_shows_error_code_for_failed_tasks(tmp_path):
    task_dir = tmp_path / "2026-05-01-failed-task"
    metadata = TaskMetadata(
        source_url="https://youtu.be/test",
        platform="youtube",
        task_dir=task_dir,
        status=TaskStatus.FAILED,
        video=VideoMetadata(title="Failed Video"),
        error=ErrorDetails(
            stage="download",
            message="auth required",
            error_code=ErrorCode.DOWNLOAD_COOKIE_AUTH,
        ),
    )
    write_metadata(metadata)
    (task_dir / "meta.json").touch()

    result = runner.invoke(
        app, ["task", "list", "--output", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "download_cookie_auth" in result.output


def test_metadata_retry_count_defaults_to_zero():
    metadata = TaskMetadata(
        source_url="https://youtu.be/test",
        platform="youtube",
        task_dir="/tmp/test",
    )
    assert metadata.retry_count == 0


def test_metadata_serializes_new_error_fields(tmp_path):
    metadata = TaskMetadata(
        source_url="https://youtu.be/test",
        platform="youtube",
        task_dir=tmp_path,
        video=VideoMetadata(title="Test"),
        error=ErrorDetails(
            stage="download",
            message="test error",
            error_code=ErrorCode.LLM_TIMEOUT,
            fix_suggestions=["increase timeout"],
        ),
        retry_count=3,
    )
    write_metadata(metadata)

    raw = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))
    assert raw["retry_count"] == 3
    assert raw["error"]["error_code"] == "llm_timeout"
    assert raw["error"]["fix_suggestions"] == ["increase timeout"]

    loaded = read_metadata(tmp_path / "meta.json")
    assert loaded.error.error_code == ErrorCode.LLM_TIMEOUT
    assert loaded.retry_count == 3


def _write_task_metadata(
    tmp_path,
    *,
    status: TaskStatus,
    platform: str = "youtube",
    source_url: str = "https://www.youtube.com/watch?v=abc",
):
    metadata = TaskMetadata(
        source_url=source_url,
        platform=platform,
        task_dir=tmp_path,
        status=status,
        video=VideoMetadata(title="Test Video"),
    )
    return write_metadata(metadata)
