import subprocess
from pathlib import Path

from video2post.audio.ffmpeg import FfmpegAudioNormalizer
from video2post.config import AppConfig
from video2post.downloader.ytdlp import YtDlpDownloader
from video2post.models import TaskStatus
from video2post.writers.metadata import read_metadata, update_status
from video2post.writers.metadata import write_metadata


def fetch_video_metadata(
    metadata_path: Path | str,
    *,
    downloader: YtDlpDownloader | None = None,
) -> object:
    metadata = read_metadata(metadata_path)
    active_downloader = downloader or YtDlpDownloader()
    try:
        video_metadata = active_downloader.fetch_metadata(metadata.source_url)
        metadata.video = video_metadata
        metadata.status = TaskStatus.METADATA_FETCHED
        write_metadata(metadata)
        return metadata
    except subprocess.CalledProcessError as error:
        update_status(
            metadata_path,
            TaskStatus.FAILED,
            error_stage=TaskStatus.METADATA_FETCHED.value,
            error_message=(error.stderr or str(error)),
            retryable=True,
        )
        raise


def prepare_audio(
    metadata_path: Path | str,
    config: AppConfig,
    *,
    downloader: YtDlpDownloader | None = None,
    normalizer: FfmpegAudioNormalizer | None = None,
) -> Path:
    metadata = read_metadata(metadata_path)
    task_dir = metadata.task_dir
    audio_path = task_dir / "audio.wav"

    if config.app.skip_existing and audio_path.exists():
        update_status(metadata_path, TaskStatus.AUDIO_NORMALIZED)
        return audio_path

    active_downloader = downloader or YtDlpDownloader(settings=config.download)
    active_normalizer = normalizer or FfmpegAudioNormalizer()

    try:
        output_template = task_dir / "source.%(ext)s"
        source_audio = active_downloader.download_audio(metadata.source_url, output_template)
        update_status(metadata_path, TaskStatus.AUDIO_DOWNLOADED)
        normalized_audio = active_normalizer.normalize(
            source_audio,
            audio_path,
            sample_rate=config.audio.sample_rate,
            channels=config.audio.channels,
        )
        update_status(metadata_path, TaskStatus.AUDIO_NORMALIZED)
        return normalized_audio
    except subprocess.CalledProcessError as error:
        failed_stage = (
            TaskStatus.AUDIO_DOWNLOADED
            if error.cmd and "yt-dlp" in str(error.cmd[0])
            else TaskStatus.AUDIO_NORMALIZED
        )
        update_status(
            metadata_path,
            TaskStatus.FAILED,
            error_stage=failed_stage.value,
            error_message=(error.stderr or str(error)),
            retryable=True,
        )
        raise
