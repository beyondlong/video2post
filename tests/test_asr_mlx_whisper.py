from pathlib import Path

from video2post.models import TranscriptSegment


class FakeMlxWhisperModule:
    def __init__(self):
        self.calls = []

    def transcribe(self, audio_path, **kwargs):
        self.calls.append((audio_path, kwargs))
        return {
            "language": "en",
            "segments": [
                {"start": 0.0, "end": 1.2, "text": "Hello Codex."},
                {"start": 1.2, "end": 2.8, "text": "This is MLX Whisper."},
            ],
        }


def test_mlx_whisper_transcriber_maps_segments(tmp_path):
    from video2post.asr.mlx_whisper import MlxWhisperTranscriber

    audio = tmp_path / "audio.wav"
    module = FakeMlxWhisperModule()
    transcriber = MlxWhisperTranscriber(module=module, model_name="mlx-community/whisper-tiny")

    segments = transcriber.transcribe(audio, language="en")

    assert segments == [
        TranscriptSegment(start=0.0, end=1.2, text="Hello Codex.", language="en"),
        TranscriptSegment(start=1.2, end=2.8, text="This is MLX Whisper.", language="en"),
    ]
    assert module.calls == [
        (
            str(Path(audio)),
            {
                "path_or_hf_repo": "mlx-community/whisper-tiny",
                "language": "en",
            },
        )
    ]
