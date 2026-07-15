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
        resolved = Path(audio_path)
        if not resolved.exists():
            raise FileNotFoundError(f"Audio file not found: {resolved}")

        model = self._model or self._load_model()
        lang = language or "zh"
        try:
            results = model.generate(input=str(resolved), language=lang)
        except Exception as exc:
            raise RuntimeError(
                f"FunASR transcription failed ({self.model_name}): {exc}"
            ) from exc

        segments = _map_results(results, lang)
        if not segments:
            raise RuntimeError(
                f"FunASR returned no segments for {resolved.name}. "
                "The audio may be silent, too short, or in an unsupported format."
            )
        return segments

    def _load_model(self) -> Any:
        try:
            from funasr import AutoModel
        except ImportError as exc:
            raise RuntimeError(
                "FunASR is not installed. Install with: pip install '.[asr-chinese]'"
            ) from exc

        try:
            self._model = AutoModel(model=self.model_name)
        except Exception as exc:
            raise RuntimeError(
                f"FunASR model '{self.model_name}' failed to load: {exc}. "
                "Try a different model or check FunASR installation."
            ) from exc
        return self._model


def _map_results(results: Any, language: str) -> list[TranscriptSegment]:
    if not results:
        return []
    first = results[0]
    sentence_info = first.get("sentence_info", []) if isinstance(first, dict) else []
    if not sentence_info and isinstance(first, dict):
        text = first.get("text", "").strip()
        if text:
            return [TranscriptSegment(start=0.0, end=0.0, text=text, language=language)]
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
