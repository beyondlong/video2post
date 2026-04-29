from video2post.models import TranscriptSegment, VideoMetadata
from video2post.writers.transcript import write_transcript


def test_write_transcript_includes_metadata_and_timestamps(tmp_path):
    target = tmp_path / "transcript.en.md"
    segments = [
        TranscriptSegment(start=0, end=15.2, text="Hello Codex.", language="en"),
        TranscriptSegment(start=75, end=90, text="Second segment.", language="en"),
    ]

    write_transcript(
        target,
        title="Test Video",
        platform="youtube",
        source_url="https://youtu.be/test",
        segments=segments,
        heading="Transcript EN",
    )

    content = target.read_text(encoding="utf-8")
    assert "# Transcript EN: Test Video" in content
    assert "- Platform: youtube" in content
    assert "- Source: https://youtu.be/test" in content
    assert "### [00:00:00 - 00:00:15]" in content
    assert "### [00:01:15 - 00:01:30]" in content
    assert "Hello Codex." in content
