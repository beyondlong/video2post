from pathlib import Path

from dotenv import load_dotenv


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _dotenv_paths() -> list[Path]:
    return [Path(".env"), _project_root() / ".env"]


def load_video2post_dotenv() -> None:
    for dotenv_path in _dotenv_paths():
        load_dotenv(dotenv_path, override=False)
