import subprocess
from collections.abc import Callable
from pathlib import Path

Runner = Callable[..., subprocess.CompletedProcess[str]]


class FfmpegAudioNormalizer:
    def __init__(self, *, runner: Runner = subprocess.run) -> None:
        self._runner = runner

    def normalize(
        self,
        source: Path | str,
        target: Path | str,
        *,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> Path:
        source_path = Path(source)
        target_path = Path(target)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        self._runner(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source_path),
                "-vn",
                "-ac",
                str(channels),
                "-ar",
                str(sample_rate),
                str(target_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return target_path
