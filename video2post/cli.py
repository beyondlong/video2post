import json
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from video2post.config import config_to_dict, load_config
from video2post.downloader.ytdlp import detect_platform
from video2post.downloader.ytdlp import YtDlpDownloader
from video2post.models import TaskMetadata, VideoMetadata
from video2post.pipeline import (
    generate_outputs,
    prepare_audio,
    transcribe_audio,
)
from video2post.samples import iter_sample_lines
from video2post.writers.metadata import read_metadata, write_metadata
from video2post.writers.workspace import create_task_workspace


app = typer.Typer(
    name="video2post",
    help="Turn technical videos into editable Chinese post drafts.",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Inspect and validate local configuration.")
app.add_typer(config_app, name="config")


@app.callback()
def main() -> None:
    """video2post command line interface."""


@app.command()
def process(
    url: Annotated[str, typer.Argument(help="YouTube or Bilibili video URL.")],
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to config.yaml."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Override configured output directory."),
    ] = None,
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
            help="Run English ASR after audio preparation.",
        ),
    ] = True,
    generate: Annotated[
        bool,
        typer.Option(
            "--generate/--no-generate",
            help="Generate derivative Markdown files with the configured LLM.",
        ),
    ] = False,
    targets: Annotated[
        str | None,
        typer.Option(
            "--targets",
            help="Comma-separated generation targets, e.g. article,script,titles.",
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
    """Process a video URL through the local pipeline."""
    loaded_config = load_config(config)
    if cleanup_source is not None:
        loaded_config.app.cleanup_source = cleanup_source
    output_dir = output or loaded_config.app.output_dir
    platform = detect_platform(url)
    video_metadata = fetch_initial_video_metadata(url) or VideoMetadata(title="untitled")
    metadata = create_task_workspace(
        output_dir=output_dir,
        source_url=url,
        platform=platform,
        title=video_metadata.title or "untitled",
    )
    metadata.video = video_metadata
    write_metadata(metadata)
    typer.echo(f"Task directory: {metadata.task_dir}")
    typer.echo(f"Platform: {platform}")
    typer.echo(
        f"Source cleanup: {'enabled' if loaded_config.app.cleanup_source else 'disabled'}"
    )

    if download:
        audio_path = prepare_audio(metadata.task_dir / "meta.json", loaded_config)
        typer.echo(f"Audio: {audio_path}")
        if transcribe:
            transcript_path = transcribe_audio(metadata.task_dir / "meta.json", loaded_config)
            typer.echo(f"Transcript: {transcript_path}")
            if generate:
                selected_targets = _parse_targets(targets)
                generated_paths = generate_outputs(
                    metadata.task_dir / "meta.json",
                    loaded_config,
                    targets=selected_targets,
                )
                for generated_path in generated_paths:
                    typer.echo(f"Generated: {generated_path}")
        else:
            typer.echo("Transcription skipped.")
    else:
        typer.echo("Download skipped.")


@app.command("generate")
def generate_command(
    task_dir: Annotated[Path, typer.Argument(help="Existing video2post task directory.")],
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to config.yaml."),
    ] = None,
    targets: Annotated[
        str | None,
        typer.Option(
            "--targets",
            help="Comma-separated generation targets, e.g. article,script,titles.",
        ),
    ] = None,
) -> None:
    """Regenerate derivative Markdown files for an existing task."""
    loaded_config = load_config(config)
    metadata_path = _metadata_path(task_dir)
    generated_paths = generate_outputs(
        metadata_path,
        loaded_config,
        targets=_parse_targets(targets),
    )
    _echo_generated_paths(generated_paths)


@app.command()
def retry(
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
            help="Comma-separated generation targets, e.g. article,script,titles.",
        ),
    ] = None,
) -> None:
    """Resume a task by running missing artifacts from its task directory."""
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
        )
        _echo_generated_paths(generated_paths)
        did_work = True

    if not did_work:
        typer.echo("Nothing to retry.")


@app.command("tasks")
def list_tasks(
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


def _parse_targets(raw_targets: str | None) -> list[str] | None:
    if not raw_targets:
        return None
    return [target.strip() for target in raw_targets.split(",") if target.strip()]


def _expected_transcript_path(metadata: VideoMetadata | TaskMetadata) -> Path:
    if metadata.platform == "bilibili":
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
        task_lines.append(
            f"{metadata.task_dir.name} | status={metadata.status.value} | artifacts={artifact_text}"
        )
    return task_lines


def _available_artifacts(task_dir: Path) -> list[str]:
    candidates = [
        ("audio.wav", "audio"),
        ("transcript.en.md", "transcript.en"),
        ("transcript.zh.md", "transcript.zh"),
        ("notes.md", "notes"),
        ("article.md", "article"),
        ("script.md", "script"),
        ("titles.md", "titles"),
    ]
    return [label for filename, label in candidates if (task_dir / filename).exists()]


def _metadata_path(task_dir: Path) -> Path:
    return task_dir / "meta.json"


def _echo_generated_paths(generated_paths: list[Path]) -> None:
    for generated_path in generated_paths:
        typer.echo(f"Generated: {generated_path}")


def fetch_initial_video_metadata(url: str) -> VideoMetadata:
    try:
        return YtDlpDownloader().fetch_metadata(url)
    except subprocess.CalledProcessError:
        return VideoMetadata(title="untitled")


if __name__ == "__main__":
    app()
