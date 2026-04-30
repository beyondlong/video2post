from pathlib import Path

from video2post.models import TaskMetadata, TaskStatus, VideoMetadata
from video2post.writers.metadata import read_metadata, update_status, write_metadata


def test_metadata_round_trip_preserves_task_state(tmp_path):
    metadata = TaskMetadata(
        source_url="https://www.youtube.com/watch?v=test",
        platform="youtube",
        video=VideoMetadata(title="Test Video", author="Test Author"),
        task_dir=tmp_path,
        status=TaskStatus.CREATED,
    )

    write_metadata(metadata)
    loaded = read_metadata(tmp_path / "meta.json")

    assert loaded.source_url == "https://www.youtube.com/watch?v=test"
    assert loaded.platform == "youtube"
    assert loaded.video.title == "Test Video"
    assert loaded.status == TaskStatus.CREATED


def test_update_status_records_error_details(tmp_path):
    metadata = TaskMetadata(
        source_url="https://example.com/bad",
        platform="unknown",
        task_dir=tmp_path,
    )
    write_metadata(metadata)

    updated = update_status(
        tmp_path / "meta.json",
        TaskStatus.FAILED,
        error_stage="metadata_fetched",
        error_message="unable to fetch metadata",
        retryable=True,
    )

    assert updated.status == TaskStatus.FAILED
    assert updated.error is not None
    assert updated.error.stage == "metadata_fetched"
    assert updated.error.message == "unable to fetch metadata"
    assert updated.error.retryable is True
