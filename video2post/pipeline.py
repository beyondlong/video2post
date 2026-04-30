import subprocess
from pathlib import Path

from video2post.audio.ffmpeg import FfmpegAudioNormalizer
from video2post.asr.faster_whisper import FasterWhisperTranscriber
from video2post.config import AppConfig
from video2post.downloader.ytdlp import YtDlpDownloader
from video2post.llm.openai_compatible import OpenAICompatibleProvider
from video2post.llm.prompts import PromptRenderer
from video2post.models import TaskMetadata, TaskStatus
from video2post.writers.markdown import write_markdown
from video2post.writers.metadata import read_metadata, update_status
from video2post.writers.metadata import write_metadata
from video2post.writers.transcript import write_transcript, write_transcript_segments


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
    segments_path = metadata.task_dir / "transcript.segments.json"
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
        write_transcript_segments(segments_path, segments)
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
        generation_transcript = _prepare_generation_transcript(
            metadata,
            transcript,
            config,
            renderer,
            active_provider,
        )
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
                    "transcript": generation_transcript,
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


def _prepare_generation_transcript(
    metadata: TaskMetadata,
    transcript: str,
    config: AppConfig,
    renderer: PromptRenderer,
    provider: OpenAICompatibleProvider,
) -> str:
    if len(transcript) <= config.generation.chunk_max_chars:
        return transcript

    chunks = _split_text_into_chunks(transcript, config.generation.chunk_max_chars)
    chunk_dir = metadata.task_dir / "chunks"
    summary_dir = metadata.task_dir / "summaries"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    summaries: list[str] = []
    chunk_count = len(chunks)
    for index, chunk in enumerate(chunks, start=1):
        chunk_path = chunk_dir / f"chunk-{index:03d}.md"
        summary_path = summary_dir / f"chunk-{index:03d}.summary.md"
        write_markdown(chunk_path, chunk)

        existing_summary = (
            summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
        )
        if existing_summary.strip():
            summaries.append(existing_summary)
            continue

        prompt = renderer.render(
            "chunk_summary",
            {
                "video_title": metadata.video.title or "untitled",
                "platform": metadata.platform,
                "source_url": metadata.source_url,
                "chunk_index": index,
                "chunk_count": chunk_count,
                "transcript_chunk": chunk,
            },
        )
        summary = provider.generate(prompt)
        write_markdown(summary_path, summary)
        summaries.append(summary)

    return "\n\n".join(summaries)


def _split_text_into_chunks(text: str, max_chars: int) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    current_parts: list[str] = []
    current_size = 0

    for paragraph in paragraphs:
        separator_size = 2 if current_parts else 0
        next_size = current_size + separator_size + len(paragraph)
        if current_parts and next_size > max_chars:
            chunks.append("\n\n".join(current_parts))
            current_parts = [paragraph]
            current_size = len(paragraph)
        else:
            current_parts.append(paragraph)
            current_size = next_size

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks or [text]
