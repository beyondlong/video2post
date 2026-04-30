from pathlib import Path
from typing import Any

from video2post.models import TranscriptSegment


class FunASRTranscriber:
    def __init__(
        self,
        *,
        model: Any | None = None,
        model_name: str = "paraformer",
    ) -> None:
        self.model_name = model_name
        self._model = model

    def transcribe(
        self,
        audio_path: Path | str,
        *,
        language: str | None = None,
    ) -> list[TranscriptSegment]:
        model = self._model or self._load_model()
        results = model.generate(input=Path(audio_path), language=language or "zh")
        return _map_results(results, language or "zh")

    def _load_model(self) -> Any:
        try:
            from funasr import AutoModel
        except ImportError as exc:
            raise RuntimeError("FunASR is not installed. Install with: pip install '.[asr-chinese]'") from exc

        self._model = AutoModel(model=self.model_name)
        return self._model


def _map_results(results: Any, language: str) -> list[TranscriptSegment]:
    if not results:
        return []
    sentence_info = results[0].get("sentence_info", [])
    return [
        TranscriptSegment(
            start=float(item.get("start", 0)) / 1000.0,
            end=float(item.get("end", 0)) / 1000.0,
            text=str(item.get("text", "")).strip(),
            language=language,
        )
        for item in sentence_info
        if str(item.get("text", "")).strip()
    ]
