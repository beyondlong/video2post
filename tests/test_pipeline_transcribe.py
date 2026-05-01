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
    transcript_text = transcript_path.read_text(encoding="utf-8")
    assert "Hello." in transcript_text
    assert "### [" not in transcript_text
    segments_path = tmp_path / "transcript.segments.json"
    assert segments_path.exists()
    assert '"start": 0.0' in segments_path.read_text(encoding="utf-8")
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


def test_transcribe_audio_groups_segments_into_paragraphs(tmp_path):
    audio = tmp_path / "audio.wav"
    audio.write_text("audio", encoding="utf-8")
    metadata = TaskMetadata(
        source_url="https://youtu.be/test",
        platform="youtube",
        task_dir=tmp_path,
        video=VideoMetadata(title="Test Video"),
    )
    write_metadata(metadata)

    class ParagraphTranscriber:
        model_name = "fake-whisper"

        def transcribe(self, audio_path, *, language=None):
            return [
                TranscriptSegment(start=0, end=1, text="First sentence.", language="en"),
                TranscriptSegment(start=1, end=2, text="Second sentence.", language="en"),
                TranscriptSegment(start=12, end=13, text="New paragraph.", language="en"),
            ]

    transcript_path = transcribe_audio(
        tmp_path / "meta.json",
        AppConfig(),
        transcriber=ParagraphTranscriber(),
    )

    transcript_text = transcript_path.read_text(encoding="utf-8")
    assert "## Paragraphs" in transcript_text
    assert "First sentence. Second sentence." in transcript_text
    assert "New paragraph." in transcript_text
    assert "\n\nFirst sentence. Second sentence.\n\nNew paragraph.\n" in transcript_text


def test_transcribe_audio_writes_chinese_transcript_for_bilibili(tmp_path):
    audio = tmp_path / "audio.wav"
    audio.write_text("audio", encoding="utf-8")
    metadata = TaskMetadata(
        source_url="https://www.bilibili.com/video/BV123",
        platform="bilibili",
        task_dir=tmp_path,
        video=VideoMetadata(title="Bilibili Video"),
    )
    write_metadata(metadata)
    transcriber = FakeTranscriber()

    transcript_path = transcribe_audio(
        tmp_path / "meta.json",
        AppConfig(),
        transcriber=transcriber,
    )

    assert transcript_path == tmp_path / "transcript.zh.md"
    assert "## Paragraphs" in transcript_path.read_text(encoding="utf-8")
    assert transcriber.calls == [(audio, "zh")]


def test_transcribe_audio_uses_funasr_for_bilibili_when_configured(monkeypatch, tmp_path):
    audio = tmp_path / "audio.wav"
    audio.write_text("audio", encoding="utf-8")
    metadata = TaskMetadata(
        source_url="https://www.bilibili.com/video/BV123",
        platform="bilibili",
        task_dir=tmp_path,
        video=VideoMetadata(title="Bilibili Video"),
    )
    write_metadata(metadata)

    class FakeChineseTranscriber:
        model_name = "fake-funasr"

        def __init__(self, *, model_name):
            self.model_name = model_name

        def transcribe(self, audio_path, *, language=None):
            return [
                TranscriptSegment(start=0, end=1, text="中文内容", language=language or "zh"),
            ]

    monkeypatch.setattr("video2post.pipeline.FunASRTranscriber", FakeChineseTranscriber)
    config = AppConfig.model_validate({"asr": {"chinese_provider": "funasr", "funasr_model": "paraformer-zh"}})

    transcript_path = transcribe_audio(tmp_path / "meta.json", config)
    loaded = read_metadata(tmp_path / "meta.json")

    assert transcript_path == tmp_path / "transcript.zh.md"
    assert loaded.asr_model == "paraformer-zh"


def test_transcribe_audio_uses_mlx_whisper_for_youtube_when_configured(monkeypatch, tmp_path):
    audio = tmp_path / "audio.wav"
    audio.write_text("audio", encoding="utf-8")
    metadata = TaskMetadata(
        source_url="https://youtu.be/test",
        platform="youtube",
        task_dir=tmp_path,
        video=VideoMetadata(title="Test Video"),
    )
    write_metadata(metadata)

    class FakeMlxWhisperTranscriber:
        model_name = "mlx-community/whisper-tiny"

        def __init__(self, *, model_name):
            self.model_name = model_name

        def transcribe(self, audio_path, *, language=None):
            return [
                TranscriptSegment(start=0, end=1, text="Hello from MLX.", language=language or "en"),
            ]

    monkeypatch.setattr("video2post.pipeline.MlxWhisperTranscriber", FakeMlxWhisperTranscriber)
    config = AppConfig.model_validate(
        {"asr": {"english_provider": "mlx_whisper", "mlx_whisper_model": "mlx-community/whisper-tiny"}}
    )

    transcript_path = transcribe_audio(tmp_path / "meta.json", config)
    loaded = read_metadata(tmp_path / "meta.json")

    assert transcript_path == tmp_path / "transcript.en.md"
    assert loaded.asr_model == "mlx-community/whisper-tiny"
