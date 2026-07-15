import subprocess
import json
import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from video2post.audio.ffmpeg import FfmpegAudioNormalizer
from video2post.audio.ffmpeg import FfmpegVideoFrameExtractor
from video2post.asr.faster_whisper import FasterWhisperTranscriber
from video2post.asr.funasr import FunASRTranscriber
from video2post.asr.mlx_whisper import MlxWhisperTranscriber
from video2post.config import AppConfig
from video2post.diagnostics import (
    classify_asr_error,
    classify_download_error,
    classify_ffmpeg_error,
    classify_llm_error,
)
from video2post.downloader.ytdlp import YtDlpDownloader
from video2post.llm.openai_compatible import LlmProviderError, OpenAICompatibleProvider
from video2post.llm.prompts import PromptRenderer
from video2post.formatters.models import Platform
from video2post.formatters.service import format_task_artifacts
from video2post.models import TaskMetadata, TaskStatus, TranscriptSegment
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
        diag = classify_download_error(error, platform=metadata.platform)
        update_status(
            metadata_path,
            TaskStatus.FAILED,
            error_stage=TaskStatus.METADATA_FETCHED.value,
            error_message=(error.stderr or str(error)),
            retryable=diag.retryable,
            error_code=diag.error_code,
            fix_suggestions=diag.fix_suggestions,
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
        if _is_local_media_source(metadata):
            source_audio = Path(metadata.source_url).expanduser()
            cleanup_after_normalize = False
        else:
            output_template = task_dir / "source.%(ext)s"
            source_audio = active_downloader.download_audio(metadata.source_url, output_template)
            cleanup_after_normalize = config.app.cleanup_source
            update_status(metadata_path, TaskStatus.AUDIO_DOWNLOADED)
        normalized_audio = active_normalizer.normalize(
            source_audio,
            audio_path,
            sample_rate=config.audio.sample_rate,
            channels=config.audio.channels,
        )
        if cleanup_after_normalize and source_audio != normalized_audio:
            source_audio.unlink(missing_ok=True)
        update_status(metadata_path, TaskStatus.AUDIO_NORMALIZED)
        return normalized_audio
    except subprocess.CalledProcessError as error:
        is_download = error.cmd and "yt-dlp" in str(error.cmd[0])
        failed_stage = "audio_download" if is_download else TaskStatus.AUDIO_NORMALIZED.value
        if is_download:
            diag = classify_download_error(error, platform=metadata.platform)
        else:
            diag = classify_ffmpeg_error(error)
        update_status(
            metadata_path,
            TaskStatus.FAILED,
            error_stage=failed_stage,
            error_message=(error.stderr or str(error)),
            retryable=diag.retryable,
            error_code=diag.error_code,
            fix_suggestions=diag.fix_suggestions,
        )
        raise


def transcribe_audio(
    metadata_path: Path | str,
    config: AppConfig,
    *,
    transcriber: object | None = None,
) -> Path:
    metadata = read_metadata(metadata_path)
    transcript_path, transcript_language, transcript_heading = _transcript_target(metadata)
    segments_path = metadata.task_dir / "transcript.segments.json"
    audio_path = metadata.task_dir / "audio.wav"

    if config.app.skip_existing and transcript_path.exists():
        update_status(metadata_path, TaskStatus.TRANSCRIBED)
        return transcript_path

    active_transcriber = transcriber or _build_transcriber(metadata, config)

    try:
        segments = active_transcriber.transcribe(audio_path, language=transcript_language)
        _validate_transcript_quality(metadata, segments)
        write_transcript(
            transcript_path,
            title=metadata.video.title or "untitled",
            platform=metadata.platform,
            source_url=metadata.source_url,
            segments=segments,
            heading=transcript_heading,
        )
        write_transcript_segments(segments_path, segments)
        metadata.asr_model = active_transcriber.model_name
        metadata.status = TaskStatus.TRANSCRIBED
        write_metadata(metadata)
        return transcript_path
    except Exception as error:
        is_quality = isinstance(error, TranscriptQualityError)
        error_stage = "transcription_quality" if is_quality else TaskStatus.TRANSCRIBED.value
        diag = classify_asr_error(error, is_quality_error=is_quality)
        update_status(
            metadata_path,
            TaskStatus.FAILED,
            error_stage=error_stage,
            error_message=str(error),
            retryable=diag.retryable,
            error_code=diag.error_code,
            fix_suggestions=diag.fix_suggestions,
        )
        raise


TARGET_OUTPUTS = {
    "translation": ("transcript.zh.md", TaskStatus.TRANSLATED_OR_CLEANED),
    "notes": ("notes.md", TaskStatus.NOTES_GENERATED),
    "cover": ("cover.jpg", TaskStatus.COVER_GENERATED),
    "x_article": ("x_article.md", TaskStatus.X_ARTICLE_GENERATED),
    "x_thread": ("x_thread.md", TaskStatus.X_THREAD_GENERATED),
    "x_titles": ("x_titles.md", TaskStatus.X_TITLES_GENERATED),
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
    downloader: YtDlpDownloader | None = None,
    cover_extractor: FfmpegVideoFrameExtractor | None = None,
    cover_at: str | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> list[Path]:
    metadata = read_metadata(metadata_path)
    selected_targets = _selected_generation_targets(metadata, config, targets)
    generated_paths: list[Path] = []
    llm_targets = [target for target in selected_targets if target not in {"cover", "publish_formats"}]

    try:
        generation_transcript = ""
        active_provider = None
        renderer = None
        if llm_targets:
            active_provider = provider or OpenAICompatibleProvider(settings=config.llm)
            renderer = PromptRenderer(prompt_dir)
            transcript = _source_transcript_path(metadata.task_dir).read_text(encoding="utf-8")
            generation_transcript = _prepare_generation_transcript(
                metadata,
                transcript,
                config,
                renderer,
                active_provider,
                progress_callback=progress_callback,
            )
        for target in selected_targets:
            if target not in TARGET_OUTPUTS and target != "publish_formats":
                raise ValueError(f"Unknown generation target: {target}")
            if target == "publish_formats":
                _report_progress(progress_callback, "Formatting publish-ready files...")
                result = format_task_artifacts(metadata.task_dir, platforms=[Platform.WECHAT, Platform.X])
                generated_paths.extend(result.paths)
                for generated_path in result.paths:
                    _report_progress(progress_callback, f"Generated {generated_path.name}")
                continue
            if target == "cover":
                generated_paths.extend(
                    _generate_cover_artifacts(
                        metadata,
                        config,
                        downloader=downloader,
                        cover_extractor=cover_extractor,
                        cover_at=cover_at,
                    )
                )
                metadata = read_metadata(metadata_path)
                continue
            filename, status = TARGET_OUTPUTS[target]
            _report_progress(progress_callback, f"Generating {target}...")
            prompt = renderer.render(
                target,
                {
                    "video_title": metadata.video.title or "untitled",
                    "platform": metadata.platform,
                    "source_url": metadata.source_url,
                    "transcript": generation_transcript,
                },
            )
            try:
                content = active_provider.generate(prompt)
            except Exception as error:
                if not _is_sensitive_llm_error(error):
                    raise
                content = _build_extractive_target_output(target, metadata, generation_transcript)
            output_path = metadata.task_dir / filename
            write_markdown(output_path, content)
            metadata.status = status
            metadata.llm_model = active_provider.model_name
            metadata.error = None
            write_metadata(metadata)
            generated_paths.append(output_path)
            _report_progress(progress_callback, f"Generated {output_path.name}")
        metadata = read_metadata(metadata_path)
        metadata.status = _derived_generation_status(metadata, config)
        metadata.error = None
        write_metadata(metadata)
        return generated_paths
    except Exception as error:
        diag = classify_llm_error(error)
        update_status(
            metadata_path,
            TaskStatus.FAILED,
            error_stage="llm_generation",
            error_message=str(error),
            retryable=diag.retryable,
            error_code=diag.error_code,
            fix_suggestions=diag.fix_suggestions,
        )
        raise


def _generate_cover_artifacts(
    metadata: TaskMetadata,
    config: AppConfig,
    *,
    downloader: YtDlpDownloader | None = None,
    cover_extractor: FfmpegVideoFrameExtractor | None = None,
    cover_at: str | None = None,
) -> list[Path]:
    active_downloader = downloader or YtDlpDownloader(settings=config.download)
    active_cover_extractor = cover_extractor or FfmpegVideoFrameExtractor()
    source_video_is_temporary = False
    if metadata.platform == "local_video":
        source_video = Path(metadata.source_url).expanduser()
    elif metadata.platform == "local_audio":
        raise ValueError("Cover generation requires a video source, but this task uses local audio.")
    else:
        source_template = metadata.task_dir / "cover-source.%(ext)s"
        source_video = active_downloader.download_video(metadata.source_url, source_template)
        source_video_is_temporary = True
    cover_path = metadata.task_dir / "cover.jpg"
    cover_meta_path = metadata.task_dir / "cover.meta.json"
    cover_seconds = _resolve_cover_time_seconds(metadata, cover_at)
    candidate_timestamps = _generate_candidate_timestamps(metadata, cover_at)

    try:
        active_cover_extractor.extract_frame(
            source_video,
            cover_path,
            at_seconds=cover_seconds,
        )
        candidate_paths: list[Path] = []
        if candidate_timestamps and hasattr(active_cover_extractor, "extract_candidates"):
            candidates_dir = metadata.task_dir / "cover-candidates"
            candidate_paths = active_cover_extractor.extract_candidates(
                source_video,
                candidates_dir,
                timestamps=candidate_timestamps,
            )
        cover_meta_path.write_text(
            json.dumps(
                {
                    "source_url": metadata.source_url,
                    "platform": metadata.platform,
                    "video_title": metadata.video.title,
                    "cover_at": cover_at,
                    "cover_at_seconds": cover_seconds,
                    "source_video": source_video.name,
                    "output_file": cover_path.name,
                    "candidate_timestamps": candidate_timestamps,
                    "candidate_count": len(candidate_paths),
                    "candidates_dir": "cover-candidates" if candidate_paths else None,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        if source_video_is_temporary:
            source_video.unlink(missing_ok=True)
        metadata.status = TaskStatus.COVER_GENERATED
        metadata.error = None
        write_metadata(metadata)
        result_paths = [cover_path, cover_meta_path]
        result_paths.extend(candidate_paths)
        return result_paths
    except Exception:
        if source_video_is_temporary:
            source_video.unlink(missing_ok=True)
        raise


def _is_local_media_source(metadata: TaskMetadata) -> bool:
    return metadata.platform in {"local_audio", "local_video", "local_file"} and Path(
        metadata.source_url
    ).expanduser().is_file()


def _resolve_cover_time_seconds(metadata: TaskMetadata, cover_at: str | None) -> float:
    if cover_at:
        return _parse_time_to_seconds(cover_at)
    duration_seconds = metadata.video.duration_seconds
    if duration_seconds:
        return float(round(duration_seconds * 0.2, 2))
    return 30.0


_CANDIDATE_COUNT = 5
_MIN_DURATION_FOR_CANDIDATES = 30


def _generate_candidate_timestamps(
    metadata: TaskMetadata,
    cover_at: str | None,
) -> list[float]:
    """Generate multiple candidate timestamps spread across the video.

    Avoids the first 5% and last 5% (likely intro/outro frames) and
    distributes candidates evenly across the middle 90%.
    """
    if cover_at:
        return []
    duration = metadata.video.duration_seconds
    if not duration or duration < _MIN_DURATION_FOR_CANDIDATES:
        return []
    margin = duration * 0.05
    usable_start = max(margin, 3.0)
    usable_end = duration - margin
    if usable_end <= usable_start:
        return []
    step = (usable_end - usable_start) / (_CANDIDATE_COUNT + 1)
    return [round(usable_start + step * i, 2) for i in range(1, _CANDIDATE_COUNT + 1)]


def _parse_time_to_seconds(value: str) -> float:
    if ":" not in value:
        return float(value)
    parts = [float(part) for part in value.split(":")]
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    raise ValueError(f"Unsupported time value: {value}")


def _prepare_generation_transcript(
    metadata: TaskMetadata,
    transcript: str,
    config: AppConfig,
    renderer: PromptRenderer,
    provider: OpenAICompatibleProvider,
    *,
    progress_callback: Callable[[str], None] | None = None,
) -> str:
    if len(transcript) <= config.generation.chunk_max_chars:
        return transcript

    _report_progress(progress_callback, "Preparing transcript chunks...")
    chunks = _build_generation_chunks(metadata, transcript, config.generation.chunk_max_chars)
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
            if _looks_like_llm_refusal(existing_summary):
                raise RuntimeError(f"Cached chunk summary is an LLM refusal: {summary_path}")
            summaries.append(existing_summary)
            continue

        _report_progress(progress_callback, f"Summarizing chunk {index}/{chunk_count}...")
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
        try:
            summary = provider.generate(prompt)
        except Exception as error:
            if not _is_sensitive_llm_error(error):
                raise
            summary = _build_extractive_chunk_summary(metadata, index, chunk_count, chunk)
        if _looks_like_llm_refusal(summary):
            raise RuntimeError(f"LLM returned a refusal while summarizing chunk {index}/{chunk_count}.")
        write_markdown(summary_path, summary)
        summaries.append(summary)

    return _prepare_global_summary(
        metadata,
        renderer,
        provider,
        summary_dir=summary_dir,
        summaries=summaries,
        progress_callback=progress_callback,
    )





def _is_sensitive_llm_error(error: Exception) -> bool:
    if isinstance(error, LlmProviderError):
        details = " ".join(
            value
            for value in [
                error.provider_error_type,
                error.provider_error_message,
                error.response_body,
                str(error),
            ]
            if value
        ).lower()
    else:
        details = str(error).lower()
    return "new_sensitive" in details or "sensitive" in details


def _build_extractive_chunk_summary(
    metadata: TaskMetadata,
    chunk_index: int,
    chunk_count: int,
    chunk: str,
) -> str:
    excerpts = _extract_transcript_excerpts(chunk, limit=8)
    lines = [
        f"# 本地抽取式片段摘要 {chunk_index}/{chunk_count}",
        "",
        "LLM 摘要被供应商安全策略拦截，已改用本地抽取式摘要。",
        "",
        f"- 视频标题：{metadata.video.title or 'untitled'}",
        f"- 平台：{metadata.platform}",
        f"- 来源：{metadata.source_url}",
        "",
        "## 原文关键摘录",
    ]
    lines.extend(f"- {excerpt}" for excerpt in excerpts)
    return "\n".join(lines).strip() + "\n"


def _build_extractive_global_summary(metadata: TaskMetadata, summaries: list[str]) -> str:
    excerpts = _extract_transcript_excerpts("\n".join(summaries), limit=12)
    lines = [
        "# 本地抽取式全局摘要",
        "",
        "LLM 全局摘要被供应商安全策略拦截，已改用局部摘要的本地抽取结果。",
        "",
        f"- 视频标题：{metadata.video.title or 'untitled'}",
        f"- 平台：{metadata.platform}",
        f"- 来源：{metadata.source_url}",
        "",
        "## 关键摘录",
    ]
    lines.extend(f"- {excerpt}" for excerpt in excerpts)
    return "\n".join(lines).strip() + "\n"


def _build_extractive_target_output(target: str, metadata: TaskMetadata, transcript: str) -> str:
    excerpts = _extract_transcript_excerpts(transcript, limit=16)
    title = metadata.video.title or "untitled"
    lines = [
        f"# {title}",
        "",
        f"> LLM 生成 `{target}` 时被供应商安全策略拦截，以下为本地抽取式草稿，可作为人工编辑底稿。",
        "",
        "## 基本信息",
        f"- 平台：{metadata.platform}",
        f"- 来源：{metadata.source_url}",
        "",
        "## 关键摘录",
    ]
    lines.extend(f"- {excerpt}" for excerpt in excerpts)
    if target == "x_thread":
        thread_lines = [f"{index + 1}. {excerpt}" for index, excerpt in enumerate(excerpts[:10])]
        lines.extend(["", "## Thread 草稿", *thread_lines])
    elif target == "x_titles":
        lines.extend(["", "## 备选标题", f"- {title}"])
    return "\n".join(lines).strip() + "\n"


def _extract_transcript_excerpts(text: str, *, limit: int) -> list[str]:
    excerpts: list[str] = []
    for raw_line in text.splitlines():
        cleaned = _clean_transcript_excerpt(raw_line)
        if len(cleaned) < 12 or cleaned in excerpts:
            continue
        excerpts.append(cleaned)
        if len(excerpts) >= limit:
            break
    if excerpts:
        return excerpts

    compact = _clean_transcript_excerpt(text)
    if not compact:
        return ["无可用摘录。"]
    return [compact[:240]]


def _clean_transcript_excerpt(text: str) -> str:
    cleaned = re.sub(r"\[[0-9:.]+\s*-\s*[0-9:.]+\]", "", text)
    cleaned = re.sub(r"[#>`*_\-]+", " ", cleaned)
    cleaned = " ".join(cleaned.split())
    return cleaned[:240]

_LLM_REFUSAL_PATTERNS = (
    "无法协助处理此内容",
    "无法协助",
    "无法处理此内容",
    "不太了解",
    "换个话题",
    "can't assist",
    "cannot assist",
    "cannot help with",
    "i'm sorry",
    "i am sorry",
)


def _looks_like_llm_refusal(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    return any(pattern in normalized for pattern in _LLM_REFUSAL_PATTERNS)

def _build_generation_chunks(metadata: TaskMetadata, transcript: str, max_chars: int) -> list[str]:
    segments = _load_transcript_segments(metadata.task_dir / "transcript.segments.json")
    if segments:
        return _split_segments_into_chunks(segments, max_chars)
    return _split_text_into_chunks(transcript, max_chars)


def _load_transcript_segments(path: Path) -> list[TranscriptSegment]:
    if not path.exists():
        return []
    raw_segments = json.loads(path.read_text(encoding="utf-8"))
    return [TranscriptSegment.model_validate(raw_segment) for raw_segment in raw_segments]


def _split_segments_into_chunks(segments: list[TranscriptSegment], max_chars: int) -> list[str]:
    chunks: list[str] = []
    current_segments: list[TranscriptSegment] = []
    current_size = 0

    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        separator_size = 1 if current_segments else 0
        next_size = current_size + separator_size + len(text)
        if current_segments and next_size > max_chars:
            chunks.append(_format_segment_chunk(current_segments))
            current_segments = [segment]
            current_size = len(text)
        else:
            current_segments.append(segment)
            current_size = next_size

    if current_segments:
        chunks.append(_format_segment_chunk(current_segments))

    return chunks


def _format_segment_chunk(segments: list[TranscriptSegment]) -> str:
    lines = [
        f"[{_format_timestamp(segment.start)} - {_format_timestamp(segment.end)}] {segment.text.strip()}"
        for segment in segments
        if segment.text.strip()
    ]
    return "\n".join(lines)


def _format_timestamp(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _prepare_global_summary(
    metadata: TaskMetadata,
    renderer: PromptRenderer,
    provider: OpenAICompatibleProvider,
    *,
    summary_dir: Path,
    summaries: list[str],
    progress_callback: Callable[[str], None] | None = None,
) -> str:
    combined_summaries = "\n\n".join(summaries)
    global_template = renderer.prompt_dir / "global_summary.md"
    if len(summaries) <= 1 or not global_template.exists():
        return combined_summaries

    global_summary_path = summary_dir / "global.summary.md"
    existing_global_summary = (
        global_summary_path.read_text(encoding="utf-8") if global_summary_path.exists() else ""
    )
    if existing_global_summary.strip():
        return existing_global_summary

    _report_progress(progress_callback, "Generating global summary...")
    prompt = renderer.render(
        "global_summary",
        {
            "video_title": metadata.video.title or "untitled",
            "platform": metadata.platform,
            "source_url": metadata.source_url,
            "chunk_summaries": combined_summaries,
        },
    )
    try:
        global_summary = provider.generate(prompt)
    except Exception as error:
        if not _is_sensitive_llm_error(error):
            raise
        global_summary = _build_extractive_global_summary(metadata, summaries)
    write_markdown(global_summary_path, global_summary)
    return global_summary


def _report_progress(progress_callback: Callable[[str], None] | None, message: str) -> None:
    if progress_callback is not None:
        progress_callback(message)


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


def _transcript_target(metadata: TaskMetadata) -> tuple[Path, str, str]:
    if _is_chinese_source(metadata):
        return metadata.task_dir / "transcript.zh.md", "zh", "Transcript ZH"
    return metadata.task_dir / "transcript.en.md", "en", "Transcript EN"


def _is_chinese_source(metadata: TaskMetadata) -> bool:
    return metadata.platform == "bilibili" or metadata.source_language == "zh"


def _source_transcript_path(task_dir: Path) -> Path:
    english = task_dir / "transcript.en.md"
    if english.exists():
        return english
    return task_dir / "transcript.zh.md"


def _selected_generation_targets(
    metadata: TaskMetadata,
    config: AppConfig,
    targets: list[str] | None,
) -> list[str]:
    if targets is not None:
        return targets
    if _is_chinese_source(metadata):
        return [target for target in config.generation.default_targets if target != "translation"]
    return config.generation.default_targets


def _is_full_generation_run(
    metadata: TaskMetadata,
    config: AppConfig,
    selected_targets: list[str],
) -> bool:
    expected_targets = _selected_generation_targets(metadata, config, None)
    return selected_targets == expected_targets


def _expected_generation_files(targets: list[str]) -> list[str]:
    files: list[str] = []
    for target in targets:
        if target == "publish_formats":
            files.extend([
                "article.wechat.md",
                "article.wechat.html",
                "x_article.x.md",
                "x_article.x.txt",
            ])
        else:
            files.append(TARGET_OUTPUTS[target][0])
    return files


def _derived_generation_status(metadata: TaskMetadata, config: AppConfig) -> TaskStatus:
    expected_targets = _selected_generation_targets(metadata, config, None)
    expected_files = _expected_generation_files(expected_targets)
    if all((metadata.task_dir / filename).exists() for filename in expected_files):
        return TaskStatus.COMPLETED

    for target in reversed(expected_targets):
        if target == "publish_formats":
            continue
        filename, status = TARGET_OUTPUTS[target]
        if (metadata.task_dir / filename).exists():
            return status
    return metadata.status


class TranscriptQualityError(RuntimeError):
    pass


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_LATIN_WORD_RE = re.compile(r"[A-Za-z]{2,}")


def _validate_transcript_quality(metadata: TaskMetadata, segments: list[TranscriptSegment]) -> None:
    text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
    if not text:
        raise TranscriptQualityError("Transcript quality check failed: ASR returned no transcript text.")

    latin_words = _LATIN_WORD_RE.findall(text.lower())
    if len(latin_words) >= 100:
        word_counts = Counter(latin_words)
        top_word, top_count = word_counts.most_common(1)[0]
        top_ratio = top_count / len(latin_words)
        unique_ratio = len(word_counts) / len(latin_words)
        if top_ratio >= 0.35 or unique_ratio <= 0.08:
            raise TranscriptQualityError(
                "Transcript quality check failed: ASR output is highly repetitive "
                f"(top word '{top_word}' appears {top_ratio:.0%} of the time)."
            )

    if _is_chinese_source(metadata):
        cjk_count = len(_CJK_RE.findall(text))
        if cjk_count < 20 and len(latin_words) >= 80:
            raise TranscriptQualityError(
                "Transcript quality check failed: Chinese source produced almost no Chinese text "
                f"({cjk_count} CJK chars, {len(latin_words)} Latin words). "
                "The ASR model may be wrong for this video, or the audio may be damaged. "
                "Try setting asr.chinese_provider to 'faster_whisper' or 'funasr' in config.yaml."
            )
        if cjk_count < 5 and len(text) > 100:
            raise TranscriptQualityError(
                "Transcript quality check failed: Chinese source produced no meaningful Chinese text. "
                "Check audio quality and ASR model configuration."
            )


def _build_transcriber(metadata: TaskMetadata, config: AppConfig) -> object:
    if _is_chinese_source(metadata):
        return _build_chinese_transcriber(config)
    if metadata.platform == "youtube" and config.asr.english_provider == "mlx_whisper":
        return MlxWhisperTranscriber(model_name=config.asr.mlx_whisper_model)
    return FasterWhisperTranscriber(model_name=config.asr.faster_whisper_model)


def _build_chinese_transcriber(config: AppConfig) -> object:
    if config.asr.chinese_provider == "funasr":
        try:
            return FunASRTranscriber(model_name=config.asr.funasr_model)
        except RuntimeError:
            return FasterWhisperTranscriber(model_name=config.asr.faster_whisper_model)
    return FasterWhisperTranscriber(model_name=config.asr.faster_whisper_model)
