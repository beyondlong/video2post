import json
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
    paragraphs = _group_segments_into_paragraphs(segments)
    lines = [
        f"# {heading}: {title}",
        "",
        f"- Platform: {platform}",
        f"- Source: {source_url}",
        f"- Generated At: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Paragraphs",
        "",
    ]
    for paragraph in paragraphs:
        lines.extend([paragraph, ""])
    return write_markdown(path, "\n".join(lines))


def write_transcript_segments(path: Path | str, segments: list[TranscriptSegment]) -> Path:
    target = Path(path)
    target.write_text(
        json.dumps([segment.model_dump(mode="json") for segment in segments], indent=2),
        encoding="utf-8",
    )
    return target


def _group_segments_into_paragraphs(
    segments: list[TranscriptSegment],
    *,
    gap_threshold_seconds: float = 6.0,
) -> list[str]:
    paragraphs: list[str] = []
    current_parts: list[str] = []
    previous_end: float | None = None

    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        if (
            current_parts
            and previous_end is not None
            and segment.start - previous_end >= gap_threshold_seconds
        ):
            paragraphs.append(" ".join(current_parts))
            current_parts = []
        current_parts.append(text)
        previous_end = segment.end

    if current_parts:
        paragraphs.append(" ".join(current_parts))

    return paragraphs
