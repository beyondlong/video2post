import re
from datetime import datetime
from pathlib import Path

from video2post.models import TaskMetadata, VideoMetadata
from video2post.writers.metadata import write_metadata


def create_task_workspace(
    *,
    output_dir: Path | str,
    source_url: str,
    platform: str,
    title: str,
) -> TaskMetadata:
    task_dir = Path(output_dir) / f"{datetime.now():%Y-%m-%d}-{_slugify(title)}"
    metadata = TaskMetadata(
        source_url=source_url,
        platform=platform,
        task_dir=task_dir,
        video=VideoMetadata(title=title),
    )
    write_metadata(metadata)
    return metadata


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "untitled"
