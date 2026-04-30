from pathlib import Path

from video2post.asr.faster_whisper import FasterWhisperTranscriber
from video2post.models import TranscriptSegment


class FakeSegment:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text


class FakeModel:
    def __init__(self):
        self.calls = []

    def transcribe(self, audio_path, **kwargs):
        self.calls.append((audio_path, kwargs))
        return (
            [
                FakeSegment(0.0, 1.5, "Hello Codex."),
                FakeSegment(1.5, 3.0, "This is a test."),
            ],
            {"language": "en"},
        )


def test_faster_whisper_transcriber_maps_segments(tmp_path):
    audio = tmp_path / "audio.wav"
    model = FakeModel()
    transcriber = FasterWhisperTranscriber(model=model, model_name="tiny")

    segments = transcriber.transcribe(audio, language="en")

    assert segments == [
        TranscriptSegment(start=0.0, end=1.5, text="Hello Codex.", language="en"),
        TranscriptSegment(start=1.5, end=3.0, text="This is a test.", language="en"),
    ]
    assert model.calls == [
        (
            Path(audio),
            {
                "language": "en",
                "vad_filter": True,
            },
        )
    ]
