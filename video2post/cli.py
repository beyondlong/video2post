import json
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from video2post.config import config_to_dict, load_config
from video2post.diagnostics import (
    classify_download_error,
    format_error_for_cli,
)
from video2post.doctor import DoctorStatus, collect_doctor_checks
from video2post.drafts import generate_draft
from video2post.downloader.ytdlp import detect_platform
from video2post.downloader.ytdlp import YtDlpDownloader
from video2post.formatters.models import parse_platforms
from video2post.formatters.service import format_markdown_file, format_task_artifacts
from video2post.models import TaskMetadata, TaskStatus, VideoMetadata
from video2post.pipeline import (
    generate_outputs,
    prepare_audio,
    transcribe_audio,
)
from video2post.samples import iter_sample_lines
from video2post.writers.metadata import read_metadata, write_metadata
from video2post.writers.workspace import create_task_workspace


ALL_GENERATION_TARGETS = "translation,notes,x_article,x_thread,x_titles,article,script,titles,cover,publish_formats"
FAST_GENERATION_TARGETS = ["notes", "x_article", "x_thread", "x_titles", "publish_formats"]
FAST_GENERATION_TARGETS_TEXT = ",".join(FAST_GENERATION_TARGETS)


app = typer.Typer(
    name="video2post",
    help="Turn technical videos into editable Chinese post drafts.",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Inspect and validate local configuration.")
task_app = typer.Typer(help="Manage existing video2post task directories.")
app.add_typer(config_app, name="config")
app.add_typer(task_app, name="task")


@app.callback()
def main() -> None:
    """video2post command line interface."""


LOCAL_AUDIO_EXTENSIONS = {
    ".aac",
    ".aiff",
    ".flac",
    ".m4a",
    ".mp3",
    ".ogg",
    ".opus",
    ".wav",
}
LOCAL_VIDEO_EXTENSIONS = {".m4v", ".mkv", ".mov", ".mp4", ".webm"}


@app.command("video")
def video_command(
    url: Annotated[
        str, typer.Argument(help="YouTube/Bilibili URL or local audio/video file path.")
    ],
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to config.yaml."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Override configured output directory."),
    ] = None,
    lang: Annotated[
        str,
        typer.Option("--lang", help="Source language: auto, en, or zh."),
    ] = "auto",
    download: Annotated[
        bool,
        typer.Option(
            "--download/--no-download",
            help="Download and normalize audio after creating the task workspace.",
        ),
    ] = True,
    transcribe: Annotated[
        bool,
        typer.Option(
            "--transcribe/--no-transcribe",
            help="Run ASR after audio preparation.",
        ),
    ] = True,
    generate: Annotated[
        bool,
        typer.Option(
            "--generate/--no-generate",
            help="Generate derivative Markdown files with the configured LLM.",
        ),
    ] = False,
    fast: Annotated[
        bool,
        typer.Option(
            "--fast/--standard",
            help=f"Run a quick creator draft and auto-generate {FAST_GENERATION_TARGETS_TEXT} unless --targets is set.",
        ),
    ] = False,
    targets: Annotated[
        str | None,
        typer.Option(
            "--targets",
            help=f"Comma-separated generation targets: {ALL_GENERATION_TARGETS}.",
        ),
    ] = None,
    cover_at: Annotated[
        str | None,
        typer.Option(
            "--cover-at",
            help="Optional screenshot time for cover generation, e.g. 00:00:30.",
        ),
    ] = None,
    cleanup_source: Annotated[
        bool | None,
        typer.Option(
            "--cleanup-source/--keep-source",
            help="Delete the compressed downloaded source after audio normalization.",
        ),
    ] = None,
) -> None:
    """Process a video URL or local audio/video file through the local pipeline.

    Fast default targets: notes,x_article,x_thread,x_titles,publish_formats.
    Supported targets: translation,notes,x_article,x_thread,x_titles,article,script,titles,cover,publish_formats.
    """
    loaded_config = load_config(config)
    if cleanup_source is not None:
        loaded_config.app.cleanup_source = cleanup_source
    output_dir = output or loaded_config.app.output_dir
    source_language = _normalize_source_language(lang)
    local_source = _resolve_local_source(url)
    if local_source is not None:
        source = str(local_source)
        platform = _detect_local_platform(local_source)
        video_metadata = _metadata_for_local_source(local_source)
    else:
        source = url
        platform = detect_platform(url)
        video_metadata = (
            fetch_initial_video_metadata(url, config=loaded_config) or VideoMetadata(title="untitled")
        )
    metadata = create_task_workspace(
        output_dir=output_dir,
        source_url=source,
        platform=platform,
        title=video_metadata.title or "untitled",
    )
    metadata.video = video_metadata
    metadata.source_language = source_language
    if (
        video_metadata.title
        or video_metadata.author
        or video_metadata.duration_seconds
        or video_metadata.published_at
    ):
        metadata.status = TaskStatus.METADATA_FETCHED
    write_metadata(metadata)
    typer.echo(f"Task directory: {metadata.task_dir}")
    typer.echo(f"Platform: {platform}")
    typer.echo(
        f"Source cleanup: {'enabled' if loaded_config.app.cleanup_source else 'disabled'}"
    )

    try:
        if download:
            audio_path = prepare_audio(metadata.task_dir / "meta.json", loaded_config)
            typer.echo(f"Audio: {audio_path}")
            if transcribe:
                transcript_path = transcribe_audio(metadata.task_dir / "meta.json", loaded_config)
                typer.echo(f"Transcript: {transcript_path}")
                if generate or fast:
                    selected_targets = _parse_process_targets(targets, fast=fast)
                    generated_paths = generate_outputs(
                        metadata.task_dir / "meta.json",
                        loaded_config,
                        targets=selected_targets,
                        cover_at=cover_at,
                        progress_callback=_echo_progress,
                    )
                    for generated_path in generated_paths:
                        typer.echo(f"Generated: {generated_path}")
            else:
                typer.echo("Transcription skipped.")
        else:
            typer.echo("Download skipped.")
    except subprocess.CalledProcessError as error:
        _handle_cli_process_error(error, platform=platform)


@task_app.command("generate")
def task_generate_command(
    task_dir: Annotated[Path, typer.Argument(help="Existing video2post task directory.")],
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to config.yaml."),
    ] = None,
    targets: Annotated[
        str | None,
        typer.Option(
            "--targets",
            help=f"Comma-separated generation targets: {ALL_GENERATION_TARGETS}.",
        ),
    ] = None,
    cover_at: Annotated[
        str | None,
        typer.Option(
            "--cover-at",
            help="Optional screenshot time for cover generation, e.g. 00:00:30.",
        ),
    ] = None,
) -> None:
    """Regenerate derivative Markdown files for an existing task.

    Supported targets: translation,notes,x_article,x_thread,x_titles,article,script,titles,cover,publish_formats.
    """
    loaded_config = load_config(config)
    metadata_path = _metadata_path(task_dir)
    generated_paths = generate_outputs(
        metadata_path,
        loaded_config,
        targets=_parse_targets(targets),
        cover_at=cover_at,
        progress_callback=_echo_progress,
    )
    _echo_generated_paths(generated_paths)


@task_app.command("retry")
def task_retry_command(
    task_dir: Annotated[Path, typer.Argument(help="Existing video2post task directory.")],
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to config.yaml."),
    ] = None,
    generate: Annotated[
        bool,
        typer.Option(
            "--generate/--no-generate",
            help="Generate derivative Markdown files after missing earlier steps are restored.",
        ),
    ] = False,
    targets: Annotated[
        str | None,
        typer.Option(
            "--targets",
            help=f"Comma-separated generation targets: {ALL_GENERATION_TARGETS}.",
        ),
    ] = None,
    cover_at: Annotated[
        str | None,
        typer.Option(
            "--cover-at",
            help="Optional screenshot time for cover generation, e.g. 00:00:30.",
        ),
    ] = None,
) -> None:
    """Resume a task by running missing artifacts from its task directory.

    Use --generate with --targets to fill selected generated outputs after audio/transcript recovery.
    """
    loaded_config = load_config(config)
    metadata_path = _metadata_path(task_dir)
    metadata = read_metadata(metadata_path)
    audio_path = metadata.task_dir / "audio.wav"
    transcript_path = _expected_transcript_path(metadata)
    did_work = False

    if not audio_path.exists():
        audio_path = prepare_audio(metadata_path, loaded_config)
        typer.echo(f"Audio: {audio_path}")
        did_work = True

    if not transcript_path.exists():
        transcript_path = transcribe_audio(metadata_path, loaded_config)
        typer.echo(f"Transcript: {transcript_path}")
        did_work = True

    if generate:
        generated_paths = generate_outputs(
            metadata_path,
            loaded_config,
            targets=_parse_targets(targets),
            cover_at=cover_at,
            progress_callback=_echo_progress,
        )
        _echo_generated_paths(generated_paths)
        did_work = True

    if not did_work:
        typer.echo("Nothing to retry.")


@app.command("draft")
def draft_command(
    content: Annotated[
        str | None,
        typer.Argument(help="Raw text content or an X/Twitter status URL to turn into X draft material."),
    ] = None,
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to config.yaml."),
    ] = None,
    mode: Annotated[
        str,
        typer.Option("--mode", help="Draft mode: x_engage or viral_280."),
    ] = "x_engage",
    x_url: Annotated[
        str | None,
        typer.Option("--x-url", help="Optional X URL. If no content is provided, the tweet text is fetched via oEmbed."),
    ] = None,
    x_fetch: Annotated[
        str,
        typer.Option("--x-fetch", help="X fetch mode when content is missing: auto, public, or browser."),
    ] = "auto",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output draft directory root. Defaults to ./drafts."),
    ] = None,
    title: Annotated[
        str | None,
        typer.Option("--title", help="Optional title used for the local draft directory slug."),
    ] = None,
) -> None:
    """Turn pasted raw material into X-ready draft content."""
    loaded_config = load_config(config)
    try:
        result = generate_draft(
            content,
            loaded_config,
            mode=mode,
            x_url=x_url,
            output_dir=output,
            title=title,
            progress_callback=_echo_progress,
            x_fetch_mode=x_fetch,
        )
    except (ValueError, RuntimeError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(f"Draft directory: {result.task_dir}")
    _echo_generated_paths(result.paths)


@app.command("format")
def format_command(
    input_path: Annotated[Path, typer.Argument(help="Markdown file or existing task directory to format.")],
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to config.yaml for --rewrite."),
    ] = None,
    platform_arg: Annotated[
        str | None,
        typer.Argument(help="Optional platform shortcut, e.g. wechat,x."),
    ] = None,
    source: Annotated[
        str | None,
        typer.Option("--source", help="Task artifact source when formatting a task directory: article,x_article,notes,transcript."),
    ] = None,
    platform: Annotated[
        str,
        typer.Option("--platform", help="Comma-separated platforms: wechat,x. WeChat writes *.wechat.md/html; X writes *.x.md/txt."),
    ] = "wechat,x",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", "-output", help="Output directory."),
    ] = None,
    rewrite: Annotated[
        bool,
        typer.Option(
            "--rewrite",
            help="Use the configured LLM to polish Markdown before deterministic formatting.",
        ),
    ] = False,
) -> None:
    """Format a Markdown file or task directory for publishing platforms.

    Platforms: wechat,x. WeChat writes *.wechat.md/html; X writes *.x.md/txt.
    """
    try:
        loaded_config = load_config(config) if rewrite or config is not None else None
        platforms = parse_platforms(platform_arg or platform)
        if input_path.is_dir():
            result = format_task_artifacts(
                input_path,
                platforms=platforms,
                source=source,
                output_dir=output,
                rewrite=rewrite,
                config=loaded_config,
            )
        else:
            result = format_markdown_file(
                input_path,
                platforms=platforms,
                output_dir=output,
                rewrite=rewrite,
                config=loaded_config,
            )
    except (ValueError, FileNotFoundError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error
    _echo_generated_paths(result.paths)


@task_app.command("status")
def task_status_command(
    task_dir: Annotated[Path, typer.Argument(help="Existing video2post task directory.")],
) -> None:
    """Show detailed status and error diagnostics for a task."""
    metadata_path = _metadata_path(task_dir)
    try:
        metadata = read_metadata(metadata_path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        typer.echo(f"Cannot read task metadata: {exc}")
        raise typer.Exit(code=1) from exc

    typer.echo(f"Task: {metadata.task_dir.name}")
    typer.echo(f"Status: {metadata.status.value}")
    typer.echo(f"Platform: {metadata.platform}")
    typer.echo(f"Source: {metadata.source_url}")
    if metadata.video.title:
        typer.echo(f"Title: {metadata.video.title}")
    if metadata.asr_model:
        typer.echo(f"ASR model: {metadata.asr_model}")
    if metadata.llm_model:
        typer.echo(f"LLM model: {metadata.llm_model}")
    if metadata.retry_count:
        typer.echo(f"Retry count: {metadata.retry_count}")

    artifacts = _available_artifacts(metadata.task_dir)
    typer.echo(f"Artifacts: {', '.join(artifacts) if artifacts else 'none'}")

    if metadata.error:
        typer.echo("")
        typer.echo(format_error_for_cli(
            metadata.error.error_code,
            metadata.error.message,
            metadata.error.fix_suggestions,
            stage=metadata.error.stage,
            retryable=metadata.error.retryable,
            task_dir=str(metadata.task_dir),
        ))


@task_app.command("list")
def task_list_command(
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to config.yaml."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Override configured output directory."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Maximum number of recent tasks to show."),
    ] = 10,
) -> None:
    """List recent task directories and their available artifacts."""
    loaded_config = load_config(config)
    output_dir = output or loaded_config.app.output_dir
    task_lines = _collect_task_lines(output_dir, limit=limit)
    for line in task_lines:
        typer.echo(line)


@app.command("samples")
def list_samples() -> None:
    """List the built-in manual regression samples."""
    for line in iter_sample_lines():
        typer.echo(line)


@app.command("doctor")
def doctor() -> None:
    """Check whether the local runtime dependencies are ready."""
    checks = collect_doctor_checks()
    has_required_missing = False

    for check in checks:
        if check.status == DoctorStatus.OK:
            label = "OK"
        elif check.status == DoctorStatus.OPTIONAL:
            label = "OPTIONAL"
        else:
            label = "MISSING"
            if check.required:
                has_required_missing = True
        typer.echo(f"[{label}] {check.name} - {check.detail}")
        if check.fix_hint and check.status != DoctorStatus.OK:
            typer.echo(f"       Fix: {check.fix_hint}")

    if has_required_missing:
        typer.echo("Doctor summary: required dependencies are missing.")
        raise typer.Exit(code=1)

    typer.echo("Doctor summary: required dependencies look ready.")


@config_app.command("show")
def show_config(
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to config.yaml."),
    ] = None,
) -> None:
    """Print the effective configuration."""
    loaded_config = load_config(config)
    typer.echo(json.dumps(config_to_dict(loaded_config), indent=2, ensure_ascii=False))


def _normalize_source_language(value: str) -> str | None:
    normalized = value.strip().lower()
    if normalized == "auto":
        return None
    if normalized in {"en", "zh"}:
        return normalized
    raise typer.BadParameter("--lang must be auto, en, or zh.")


def _parse_targets(raw_targets: str | None) -> list[str] | None:
    if not raw_targets:
        return None
    return [target.strip() for target in raw_targets.split(",") if target.strip()]


def _parse_process_targets(raw_targets: str | None, *, fast: bool) -> list[str] | None:
    parsed_targets = _parse_targets(raw_targets)
    if parsed_targets is not None:
        return parsed_targets
    if fast:
        return FAST_GENERATION_TARGETS.copy()
    return None


def _resolve_local_source(value: str) -> Path | None:
    path = Path(value).expanduser()
    if path.is_file():
        return path.resolve()
    return None


def _detect_local_platform(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in LOCAL_AUDIO_EXTENSIONS:
        return "local_audio"
    if suffix in LOCAL_VIDEO_EXTENSIONS:
        return "local_video"
    return "local_file"


def _metadata_for_local_source(path: Path) -> VideoMetadata:
    return VideoMetadata(title=path.stem)


def _expected_transcript_path(metadata: VideoMetadata | TaskMetadata) -> Path:
    if metadata.platform == "bilibili" or getattr(metadata, "source_language", None) == "zh":
        return metadata.task_dir / "transcript.zh.md"
    return metadata.task_dir / "transcript.en.md"


def _collect_task_lines(output_dir: Path, *, limit: int) -> list[str]:
    metadata_files = sorted(
        output_dir.glob("*/meta.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    task_lines: list[str] = []
    for metadata_path in metadata_files[:limit]:
        metadata = read_metadata(metadata_path)
        artifacts = _available_artifacts(metadata.task_dir)
        artifact_text = ", ".join(artifacts) if artifacts else "no artifacts yet"
        status_text = metadata.status.value
        if metadata.error and metadata.error.error_code.value != "unknown":
            status_text += f" ({metadata.error.error_code.value})"
        task_lines.append(
            f"{metadata.task_dir.name} | status={status_text} | artifacts={artifact_text}"
        )
    return task_lines


def _available_artifacts(task_dir: Path) -> list[str]:
    candidates = [
        ("audio.wav", "audio"),
        ("transcript.en.md", "transcript.en"),
        ("transcript.zh.md", "transcript.zh"),
        ("notes.md", "notes"),
        ("cover.jpg", "cover"),
        ("x_article.md", "x_article"),
        ("x_thread.md", "x_thread"),
        ("x_titles.md", "x_titles"),
        ("article.md", "article"),
        ("script.md", "script"),
        ("titles.md", "titles"),
        ("article.wechat.md", "article.wechat.md"),
        ("article.wechat.html", "article.wechat.html"),
        ("x_article.x.md", "x_article.x.md"),
        ("x_article.x.txt", "x_article.x.txt"),
    ]
    return [label for filename, label in candidates if (task_dir / filename).exists()]


def _metadata_path(task_dir: Path) -> Path:
    return task_dir / "meta.json"


def _echo_generated_paths(generated_paths: list[Path]) -> None:
    for generated_path in generated_paths:
        typer.echo(f"Generated: {generated_path}")


def _echo_progress(message: str) -> None:
    typer.echo(f"Progress: {message}")


def fetch_initial_video_metadata(url: str, config=None) -> VideoMetadata:
    try:
        downloader = YtDlpDownloader(settings=config.download if config else None)
        return downloader.fetch_metadata(url)
    except subprocess.CalledProcessError:
        return VideoMetadata(title="untitled")


def _handle_cli_process_error(error: subprocess.CalledProcessError, *, platform: str) -> None:
    diag = classify_download_error(error, platform=platform)
    typer.echo(format_error_for_cli(
        diag.error_code,
        (error.stderr or str(error)).strip(),
        diag.fix_suggestions,
        stage="download",
        retryable=diag.retryable,
    ))
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
