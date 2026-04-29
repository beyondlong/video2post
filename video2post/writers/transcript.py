from datetime import datetime
from pathlib import Path

from video2post.models import TranscriptSegment
from video2post.writers.markdown import write_markdown


def write_transcript(
    path: Path | str,
    *,
    title: str,
    platform: str,
    source_url: str,
    segments: list[TranscriptSegment],
    heading: str,
) -> Path:
    lines = [
        f"# {heading}: {title}",
        "",
        f"- Platform: {platform}",
        f"- Source: {source_url}",
        f"- Generated At: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Segments",
        "",
    ]
    for segment in segments:
        lines.extend(
            [
                f"### [{_format_timestamp(segment.start)} - {_format_timestamp(segment.end)}]",
                "",
                segment.text,
                "",
            ]
        )
    return write_markdown(path, "\n".join(lines))


def _format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    remaining_seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"
