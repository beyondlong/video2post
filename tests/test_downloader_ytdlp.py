import json
import subprocess

from video2post.downloader.ytdlp import YtDlpDownloader, detect_platform
from video2post.models import VideoMetadata


class FakeRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if "--dump-json" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "title": "Test Video",
                        "uploader": "Test Author",
                        "duration": 123,
                        "upload_date": "20260429",
                    }
                ),
                stderr="",
            )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


def test_detect_platform_supports_youtube_and_bilibili():
    assert detect_platform("https://www.youtube.com/watch?v=abc") == "youtube"
    assert detect_platform("https://youtu.be/abc") == "youtube"
    assert detect_platform("https://www.bilibili.com/video/BV123") == "bilibili"
    assert detect_platform("https://example.com/video") == "unknown"


def test_fetch_metadata_maps_ytdlp_json():
    runner = FakeRunner()
    downloader = YtDlpDownloader(runner=runner)

    metadata = downloader.fetch_metadata("https://www.youtube.com/watch?v=abc")

    assert metadata == VideoMetadata(
        title="Test Video",
        author="Test Author",
        duration_seconds=123,
        published_at="20260429",
    )
    command, kwargs = runner.calls[0]
    assert command[:3] == ["yt-dlp", "--dump-json", "--no-playlist"]
    assert kwargs["check"] is True
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True


def test_fetch_metadata_normalizes_float_duration_seconds():
    def runner(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {
                    "title": "Bilibili Video",
                    "uploader": "Uploader",
                    "duration": 816.808,
                    "upload_date": "20260430",
                }
            ),
            stderr="",
        )

    downloader = YtDlpDownloader(runner=runner)

    metadata = downloader.fetch_metadata("https://www.bilibili.com/video/BV123")

    assert metadata.duration_seconds == 817


def test_download_audio_builds_expected_command(tmp_path):
    runner = FakeRunner()
    downloader = YtDlpDownloader(runner=runner)
    target = tmp_path / "source.%(ext)s"

    downloader.download_audio("https://youtu.be/abc", target)

    command, kwargs = runner.calls[0]
    assert command[:4] == ["yt-dlp", "--no-playlist", "-f", "bestaudio/best"]
    assert "--extract-audio" not in command
    assert "--audio-format" not in command
    assert command[command.index("-o") + 1] == str(target)
    assert command[-1] == "https://youtu.be/abc"
    assert kwargs["check"] is True
