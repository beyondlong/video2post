from pathlib import Path
from typing import Any

from video2post.models import TranscriptSegment


class FasterWhisperTranscriber:
    def __init__(
        self,
        *,
        model: Any | None = None,
        model_name: str = "medium",
        device: str = "auto",
        compute_type: str = "default",
    ) -> None:
        self.model_name = model_name
        self._model = model
        self._device = device
        self._compute_type = compute_type

    def transcribe(
        self,
        audio_path: Path | str,
        *,
        language: str | None = None,
    ) -> list[TranscriptSegment]:
        model = self._model or self._load_model()
        kwargs = {"language": language, "vad_filter": True}
        segments, info = model.transcribe(Path(audio_path), **kwargs)
        detected_language = _read_language(info) or language
        return [
            TranscriptSegment(
                start=float(segment.start),
                end=float(segment.end),
                text=segment.text.strip(),
                language=detected_language,
            )
            for segment in segments
        ]

    def _load_model(self) -> Any:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is not installed. Install with: pip install '.[asr]'"
            ) from exc

        self._model = WhisperModel(
            self.model_name,
            device=self._device,
            compute_type=self._compute_type,
        )
        return self._model


def _read_language(info: Any) -> str | None:
    if isinstance(info, dict):
        return info.get("language")
    return getattr(info, "language", None)
