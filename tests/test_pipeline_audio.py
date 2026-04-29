import subprocess

from video2post.config import AppConfig
from video2post.models import TaskMetadata, TaskStatus, VideoMetadata
from video2post.pipeline import fetch_video_metadata, prepare_audio
from video2post.writers.metadata import read_metadata, write_metadata


class FakeDownloader:
    def __init__(self):
        self.downloads = []

    def fetch_metadata(self, url):
        return VideoMetadata(title="Fetched", author="Author", duration_seconds=10)

    def download_audio(self, url, output_template):
        self.downloads.append((url, output_template))
        source = output_template.with_name("downloaded.m4a")
        source.write_text("audio", encoding="utf-8")
        return source


class FakeNormalizer:
    def __init__(self):
        self.calls = []

    def normalize(self, source, target, *, sample_rate=16000, channels=1):
        self.calls.append((source, target, sample_rate, channels))
        target.write_text("wav", encoding="utf-8")
        return target


def test_prepare_audio_downloads_normalizes_and_updates_metadata(tmp_path):
    metadata = TaskMetadata(
        source_url="https://youtu.be/abc",
        platform="youtube",
        task_dir=tmp_path,
        video=VideoMetadata(title="Test"),
    )
    write_metadata(metadata)
    downloader = FakeDownloader()
    normalizer = FakeNormalizer()

    audio_path = prepare_audio(
        tmp_path / "meta.json",
        AppConfig(),
        downloader=downloader,
        normalizer=normalizer,
    )

    loaded = read_metadata(tmp_path / "meta.json")
    assert audio_path == tmp_path / "audio.wav"
    assert loaded.status == TaskStatus.AUDIO_NORMALIZED
    assert downloader.downloads[0][0] == "https://youtu.be/abc"
    assert normalizer.calls[0][1] == tmp_path / "audio.wav"


def test_prepare_audio_records_failure(tmp_path):
    class FailingDownloader:
        def download_audio(self, url, output_template):
            raise subprocess.CalledProcessError(1, ["yt-dlp"], stderr="boom")

    metadata = TaskMetadata(
        source_url="https://youtu.be/abc",
        platform="youtube",
        task_dir=tmp_path,
    )
    write_metadata(metadata)

    try:
        prepare_audio(
            tmp_path / "meta.json",
            AppConfig(),
            downloader=FailingDownloader(),
            normalizer=FakeNormalizer(),
        )
    except subprocess.CalledProcessError:
        pass

    loaded = read_metadata(tmp_path / "meta.json")
    assert loaded.status == TaskStatus.FAILED
    assert loaded.error is not None
    assert loaded.error.stage == TaskStatus.AUDIO_DOWNLOADED.value
    assert loaded.error.retryable is True


def test_fetch_video_metadata_updates_metadata_status(tmp_path):
    metadata = TaskMetadata(
        source_url="https://youtu.be/abc",
        platform="youtube",
        task_dir=tmp_path,
    )
    write_metadata(metadata)

    updated = fetch_video_metadata(
        tmp_path / "meta.json",
        downloader=FakeDownloader(),
    )

    loaded = read_metadata(tmp_path / "meta.json")
    assert updated.video.title == "Fetched"
    assert loaded.video.author == "Author"
    assert loaded.status == TaskStatus.METADATA_FETCHED
