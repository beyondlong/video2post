from video2post.models import TranscriptSegment
from video2post.writers.transcript import write_transcript, write_transcript_segments


def test_write_transcript_includes_metadata_and_paragraphs(tmp_path):
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
    assert "## Paragraphs" in content
    assert "### [" not in content
    assert "Hello Codex." in content
    assert "Second segment." in content


def test_write_transcript_segments_writes_json_dump(tmp_path):
    target = tmp_path / "transcript.segments.json"
    segments = [
        TranscriptSegment(start=0, end=1.5, text="Hello Codex.", language="en"),
    ]

    write_transcript_segments(target, segments)

    content = target.read_text(encoding="utf-8")
    assert '"start": 0.0' in content
    assert '"end": 1.5' in content
    assert '"text": "Hello Codex."' in content
