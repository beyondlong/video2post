import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

from video2post.config import DownloadSettings
from video2post.models import VideoMetadata

Runner = Callable[..., subprocess.CompletedProcess[str]]


def detect_platform(url: str) -> str:
    hostname = urlparse(url).hostname or ""
    normalized = hostname.lower()
    if normalized in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}:
        return "youtube"
    if normalized.endswith("bilibili.com"):
        return "bilibili"
    return "unknown"


class YtDlpDownloader:
    def __init__(
        self,
        *,
        settings: DownloadSettings | None = None,
        runner: Runner = subprocess.run,
    ) -> None:
        self._settings = settings or DownloadSettings()
        self._runner = runner

    def fetch_metadata(self, url: str) -> VideoMetadata:
        result = self._runner(
            self._base_command(["--dump-json", "--no-playlist", url]),
            check=True,
            capture_output=True,
            text=True,
        )
        raw = json.loads(result.stdout)
        return VideoMetadata(
            title=raw.get("title"),
            author=raw.get("uploader") or raw.get("channel"),
            duration_seconds=_normalize_duration_seconds(raw.get("duration")),
            published_at=raw.get("upload_date") or raw.get("release_date"),
        )

    def download_audio(self, url: str, output_template: Path | str) -> Path:
        output = Path(output_template)
        output.parent.mkdir(parents=True, exist_ok=True)
        command = self._base_command(
            [
                "--no-playlist",
                "-f",
                "bestaudio/best",
                "-o",
                str(output),
                url,
            ]
        )
        self._runner(command, check=True)
        return _resolve_downloaded_audio(output, self._settings.preferred_audio_format)

    def _base_command(self, args: list[str]) -> list[str]:
        command = ["yt-dlp"]
        if self._settings.cookies_file:
            command.extend(["--cookies", str(self._settings.cookies_file)])
        if self._settings.cookies_from_browser:
            command.extend(["--cookies-from-browser", self._settings.cookies_from_browser])
        command.extend(args)
        return command


def _resolve_downloaded_audio(output_template: Path, preferred_format: str) -> Path:
    if "%(ext)s" in output_template.name:
        candidate = output_template.with_name(
            output_template.name.replace("%(ext)s", preferred_format)
        )
        if candidate.exists():
            return candidate
    if output_template.exists():
        return output_template
    matches = sorted(output_template.parent.glob(output_template.name.replace("%(ext)s", "*")))
    return matches[0] if matches else output_template


def _normalize_duration_seconds(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value)
    return int(value)
