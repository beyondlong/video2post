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
