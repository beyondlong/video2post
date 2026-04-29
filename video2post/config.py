from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    output_dir: Path = Path("outputs")
    keep_audio: bool = True
    skip_existing: bool = True


class DownloadSettings(BaseModel):
    preferred_audio_format: str = "wav"
    cookies_file: Path | None = None
    cookies_from_browser: str | None = None


class AudioSettings(BaseModel):
    sample_rate: int = 16000
    channels: int = 1


class AsrSettings(BaseModel):
    default_language: str = "auto"
    english_provider: str = "faster_whisper"
    chinese_provider: str = "funasr"
    faster_whisper_model: str = "medium"
    funasr_model: str = "paraformer"


class LlmSettings(BaseModel):
    provider: str = "openai_compatible"
    base_url: str | None = None
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096


class GenerationSettings(BaseModel):
    default_targets: list[str] = Field(
        default_factory=lambda: [
            "translation",
            "notes",
            "article",
            "script",
            "titles",
        ]
    )
    chunk_max_chars: int = 6000


class AppConfig(BaseModel):
    app: AppSettings = Field(default_factory=AppSettings)
    download: DownloadSettings = Field(default_factory=DownloadSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    asr: AsrSettings = Field(default_factory=AsrSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    generation: GenerationSettings = Field(default_factory=GenerationSettings)


def load_config(path: Path | str | None = None) -> AppConfig:
    config_path = Path(path) if path else Path("config.yaml")
    if not config_path.exists():
        return AppConfig()

    raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw_config, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {config_path}")

    return AppConfig.model_validate(raw_config)


def config_to_dict(config: AppConfig) -> dict[str, Any]:
    return config.model_dump(mode="json")
