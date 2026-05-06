from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Platform(StrEnum):
    WECHAT = "wechat"
    X = "x"


def parse_platforms(value: str | None) -> list[Platform]:
    raw_values = [part.strip() for part in (value or "wechat,x").split(",")]
    platforms: list[Platform] = []
    for raw_value in raw_values:
        if not raw_value:
            continue
        try:
            platform = Platform(raw_value)
        except ValueError as error:
            raise ValueError(f"Unsupported platform: {raw_value}") from error
        if platform not in platforms:
            platforms.append(platform)
    return platforms


@dataclass(frozen=True)
class PlatformOutput:
    platform: Platform
    path: Path
    kind: str


@dataclass(frozen=True)
class FormatResult:
    outputs: list[PlatformOutput] = field(default_factory=list)

    @property
    def paths(self) -> list[Path]:
        return [output.path for output in self.outputs]


@dataclass(frozen=True)
class FormatRequest:
    input_path: Path
    platforms: list[Platform]
    output_dir: Path | None = None
    rewrite: bool = False

    def __post_init__(self) -> None:
        if self.output_dir is None:
            object.__setattr__(self, "output_dir", self.input_path.parent)


@dataclass(frozen=True)
class MarkdownBlock:
    kind: str
    text: str = ""
    level: int | None = None
    language: str | None = None
    items: list[str] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


@dataclass(frozen=True)
class MarkdownDocument:
    blocks: list[MarkdownBlock]
