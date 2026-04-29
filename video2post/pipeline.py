import subprocess
from pathlib import Path

from video2post.audio.ffmpeg import FfmpegAudioNormalizer
from video2post.asr.faster_whisper import FasterWhisperTranscriber
from video2post.config import AppConfig
from video2post.downloader.ytdlp import YtDlpDownloader
from video2post.llm.openai_compatible import OpenAICompatibleProvider
from video2post.llm.prompts import PromptRenderer
from video2post.models import TaskStatus
from video2post.writers.markdown import write_markdown
from video2post.writers.metadata import read_metadata, update_status
from video2post.writers.metadata import write_metadata
from video2post.writers.transcript import write_transcript


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
        if config.app.cleanup_source and source_audio != normalized_audio:
            source_audio.unlink(missing_ok=True)
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


def transcribe_audio(
    metadata_path: Path | str,
    config: AppConfig,
    *,
    transcriber: FasterWhisperTranscriber | None = None,
) -> Path:
    metadata = read_metadata(metadata_path)
    transcript_path = metadata.task_dir / "transcript.en.md"
    audio_path = metadata.task_dir / "audio.wav"

    if config.app.skip_existing and transcript_path.exists():
        update_status(metadata_path, TaskStatus.TRANSCRIBED)
        return transcript_path

    active_transcriber = transcriber or FasterWhisperTranscriber(
        model_name=config.asr.faster_whisper_model
    )

    try:
        segments = active_transcriber.transcribe(audio_path, language="en")
        write_transcript(
            transcript_path,
            title=metadata.video.title or "untitled",
            platform=metadata.platform,
            source_url=metadata.source_url,
            segments=segments,
            heading="Transcript EN",
        )
        metadata.asr_model = active_transcriber.model_name
        metadata.status = TaskStatus.TRANSCRIBED
        write_metadata(metadata)
        return transcript_path
    except Exception as error:
        update_status(
            metadata_path,
            TaskStatus.FAILED,
            error_stage=TaskStatus.TRANSCRIBED.value,
            error_message=str(error),
            retryable=True,
        )
        raise


TARGET_OUTPUTS = {
    "translation": ("transcript.zh.md", TaskStatus.TRANSLATED_OR_CLEANED),
    "notes": ("notes.md", TaskStatus.NOTES_GENERATED),
    "article": ("article.md", TaskStatus.ARTICLE_GENERATED),
    "script": ("script.md", TaskStatus.SCRIPT_GENERATED),
    "titles": ("titles.md", TaskStatus.TITLES_GENERATED),
}


def generate_outputs(
    metadata_path: Path | str,
    config: AppConfig,
    *,
    provider: OpenAICompatibleProvider | None = None,
    prompt_dir: Path | str = "prompts",
    targets: list[str] | None = None,
) -> list[Path]:
    metadata = read_metadata(metadata_path)
    active_provider = provider or OpenAICompatibleProvider(settings=config.llm)
    renderer = PromptRenderer(prompt_dir)
    selected_targets = targets or config.generation.default_targets
    transcript = (metadata.task_dir / "transcript.en.md").read_text(encoding="utf-8")
    generated_paths: list[Path] = []

    try:
        for target in selected_targets:
            if target not in TARGET_OUTPUTS:
                raise ValueError(f"Unknown generation target: {target}")
            filename, status = TARGET_OUTPUTS[target]
            prompt = renderer.render(
                target,
                {
                    "video_title": metadata.video.title or "untitled",
                    "platform": metadata.platform,
                    "source_url": metadata.source_url,
                    "transcript": transcript,
                },
            )
            content = active_provider.generate(prompt)
            output_path = metadata.task_dir / filename
            write_markdown(output_path, content)
            metadata.status = status
            metadata.llm_model = active_provider.model_name
            write_metadata(metadata)
            generated_paths.append(output_path)
        return generated_paths
    except Exception as error:
        update_status(
            metadata_path,
            TaskStatus.FAILED,
            error_stage="llm_generation",
            error_message=str(error),
            retryable=True,
        )
        raise
