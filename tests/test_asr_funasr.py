import pytest

from video2post.asr.funasr import FunASRTranscriber
from video2post.models import TranscriptSegment


class FakeFunASRModel:
    def __init__(self):
        self.calls = []

    def generate(self, input, **kwargs):
        self.calls.append((input, kwargs))
        return [
            {
                "sentence_info": [
                    {"start": 0, "end": 1250, "text": "你好，Codex。"},
                    {"start": 1250, "end": 3000, "text": "这是一个测试。"},
                ]
            }
        ]


def test_funasr_transcriber_maps_segments(tmp_path):
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"audio")
    model = FakeFunASRModel()
    transcriber = FunASRTranscriber(model=model, model_name="paraformer")

    segments = transcriber.transcribe(audio, language="zh")

    assert segments == [
        TranscriptSegment(start=0.0, end=1.25, text="你好，Codex。", language="zh"),
        TranscriptSegment(start=1.25, end=3.0, text="这是一个测试。", language="zh"),
    ]
    assert model.calls == [
        (
            str(audio),
            {
                "language": "zh",
            },
        )
    ]


def test_funasr_raises_on_missing_audio_file(tmp_path):
    transcriber = FunASRTranscriber(model=FakeFunASRModel())

    with pytest.raises(FileNotFoundError, match="Audio file not found"):
        transcriber.transcribe(tmp_path / "nonexistent.wav", language="zh")


def test_funasr_raises_on_empty_results(tmp_path):
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"audio")

    class EmptyModel:
        def generate(self, input, **kwargs):
            return [{"sentence_info": []}]

    transcriber = FunASRTranscriber(model=EmptyModel())

    with pytest.raises(RuntimeError, match="no segments"):
        transcriber.transcribe(audio, language="zh")


def test_funasr_wraps_model_exceptions(tmp_path):
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"audio")

    class FailModel:
        def generate(self, input, **kwargs):
            raise ValueError("CUDA error")

    transcriber = FunASRTranscriber(model=FailModel())

    with pytest.raises(RuntimeError, match="FunASR transcription failed"):
        transcriber.transcribe(audio, language="zh")


def test_funasr_handles_text_only_result_without_sentence_info(tmp_path):
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"audio")

    class TextOnlyModel:
        def generate(self, input, **kwargs):
            return [{"text": "整段中文文本没有时间戳"}]

    transcriber = FunASRTranscriber(model=TextOnlyModel())
    segments = transcriber.transcribe(audio, language="zh")

    assert len(segments) == 1
    assert segments[0].text == "整段中文文本没有时间戳"
    assert segments[0].language == "zh"
