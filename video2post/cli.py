import json
from pathlib import Path
from typing import Annotated

import typer

from video2post.config import config_to_dict, load_config
from video2post.downloader.ytdlp import detect_platform
from video2post.pipeline import fetch_video_metadata, prepare_audio
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
) -> None:
    """Process a video URL through the local pipeline."""
    loaded_config = load_config(config)
    output_dir = output or loaded_config.app.output_dir
    platform = detect_platform(url)
    metadata = create_task_workspace(
        output_dir=output_dir,
        source_url=url,
        platform=platform,
        title="untitled",
    )
    typer.echo(f"Task directory: {metadata.task_dir}")
    typer.echo(f"Platform: {platform}")

    if download:
        fetch_video_metadata(metadata.task_dir / "meta.json")
        audio_path = prepare_audio(metadata.task_dir / "meta.json", loaded_config)
        typer.echo(f"Audio: {audio_path}")
    else:
        typer.echo("Download skipped.")


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
