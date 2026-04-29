from video2post.config import AppConfig
from video2post.models import TaskMetadata, TaskStatus, TranscriptSegment, VideoMetadata
from video2post.pipeline import transcribe_audio
from video2post.writers.metadata import read_metadata, write_metadata


class FakeTranscriber:
    model_name = "fake-whisper"

    def __init__(self):
        self.calls = []

    def transcribe(self, audio_path, *, language=None):
        self.calls.append((audio_path, language))
        return [
            TranscriptSegment(start=0, end=1, text="Hello.", language=language or "en"),
        ]


def test_transcribe_audio_writes_english_transcript_and_updates_metadata(tmp_path):
    audio = tmp_path / "audio.wav"
    audio.write_text("audio", encoding="utf-8")
    metadata = TaskMetadata(
        source_url="https://youtu.be/test",
        platform="youtube",
        task_dir=tmp_path,
        video=VideoMetadata(title="Test Video"),
    )
    write_metadata(metadata)
    transcriber = FakeTranscriber()

    transcript_path = transcribe_audio(
        tmp_path / "meta.json",
        AppConfig(),
        transcriber=transcriber,
    )

    loaded = read_metadata(tmp_path / "meta.json")
    assert transcript_path == tmp_path / "transcript.en.md"
    assert transcript_path.exists()
    assert "Hello." in transcript_path.read_text(encoding="utf-8")
    assert loaded.status == TaskStatus.TRANSCRIBED
    assert loaded.asr_model == "fake-whisper"
    assert transcriber.calls == [(audio, "en")]


def test_transcribe_audio_skips_existing_transcript(tmp_path):
    audio = tmp_path / "audio.wav"
    audio.write_text("audio", encoding="utf-8")
    transcript = tmp_path / "transcript.en.md"
    transcript.write_text("existing", encoding="utf-8")
    metadata = TaskMetadata(
        source_url="https://youtu.be/test",
        platform="youtube",
        task_dir=tmp_path,
    )
    write_metadata(metadata)
    transcriber = FakeTranscriber()

    transcript_path = transcribe_audio(
        tmp_path / "meta.json",
        AppConfig(),
        transcriber=transcriber,
    )

    loaded = read_metadata(tmp_path / "meta.json")
    assert transcript_path == transcript
    assert transcriber.calls == []
    assert loaded.status == TaskStatus.TRANSCRIBED
