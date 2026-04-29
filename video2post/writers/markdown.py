from pathlib import Path


def write_markdown(path: Path | str, content: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized = content if content.endswith("\n") else f"{content}\n"
    target.write_text(normalized, encoding="utf-8")
    return target
