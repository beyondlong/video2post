from pathlib import Path
from typing import Any

from video2post.models import TranscriptSegment


class MlxWhisperTranscriber:
    def __init__(
        self,
        *,
        module: Any | None = None,
        model_name: str = "mlx-community/whisper-tiny",
    ) -> None:
        self.model_name = model_name
        self._module = module

    def transcribe(
        self,
        audio_path: Path | str,
        *,
        language: str | None = None,
    ) -> list[TranscriptSegment]:
        module = self._module or self._load_module()
        result = module.transcribe(
            str(Path(audio_path)),
            path_or_hf_repo=self.model_name,
            language=language,
        )
        return _map_result(result, language)

    def _load_module(self) -> Any:
        try:
            import mlx_whisper
        except ImportError as exc:
            raise RuntimeError(
                "mlx-whisper is not installed. Install with: pip install mlx-whisper"
            ) from exc
        self._module = mlx_whisper
        return self._module


def _map_result(result: Any, requested_language: str | None) -> list[TranscriptSegment]:
    language = requested_language or result.get("language")
    return [
        TranscriptSegment(
            start=float(segment.get("start", 0.0)),
            end=float(segment.get("end", 0.0)),
            text=str(segment.get("text", "")).strip(),
            language=language,
        )
        for segment in result.get("segments", [])
        if str(segment.get("text", "")).strip()
    ]
