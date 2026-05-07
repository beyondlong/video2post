from pathlib import Path

from video2post.formatters.models import Platform

_SOURCE_FILES = {
    "article": ["article.md"],
    "x_article": ["x_article.md"],
    "notes": ["notes.md"],
    "transcript": ["transcript.en.md", "transcript.zh.md"],
}


def resolve_task_source(
    task_dir: Path | str,
    *,
    source: str | None,
    platform: Platform,
) -> Path:
    task_path = Path(task_dir)
    metadata_path = task_path / "meta.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Task metadata not found: {metadata_path}")

    source_names = _source_candidates(source, platform)
    for source_name in source_names:
        for filename in _SOURCE_FILES[source_name]:
            candidate = task_path / filename
            if candidate.exists():
                return candidate

    requested = source or platform.value
    raise FileNotFoundError(f"Task source not found for {requested}: {task_path}")


def _source_candidates(source: str | None, platform: Platform) -> list[str]:
    if source:
        if source not in _SOURCE_FILES:
            raise ValueError(f"Unsupported task source: {source}")
        return [source]
    if platform == Platform.WECHAT:
        return ["article", "x_article"]
    if platform == Platform.X:
        return ["x_article", "article"]
    return ["article"]
