import json
from pathlib import Path
from typing import Annotated

import typer

from video2post.config import config_to_dict, load_config


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
) -> None:
    """Process a video URL through the local pipeline."""
    _ = load_config(config)
    typer.echo("Pipeline is not implemented yet.")
    typer.echo(f"URL: {url}")


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
