from pathlib import Path

from video2post.formatters.markdown_parser import parse_markdown
from video2post.formatters.models import FormatResult, Platform, PlatformOutput
from video2post.formatters.rewrite import rewrite_markdown
from video2post.formatters.task_sources import resolve_task_source
from video2post.formatters.wechat import render_wechat_html, render_wechat_markdown
from video2post.formatters.x_longform import render_x_markdown, render_x_text


def format_markdown_file(
    input_path: Path | str,
    *,
    platforms: list[Platform],
    output_dir: Path | str | None = None,
    rewrite: bool = False,
) -> FormatResult:
    source_path = Path(input_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Markdown input not found: {source_path}")
    target_dir = Path(output_dir) if output_dir is not None else source_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    content = source_path.read_text(encoding="utf-8")
    if rewrite:
        content = rewrite_markdown(content, platforms)

    document = parse_markdown(content)
    outputs: list[PlatformOutput] = []
    stem = source_path.stem

    if Platform.WECHAT in platforms:
        markdown_path = target_dir / f"{stem}.wechat.md"
        html_path = target_dir / f"{stem}.wechat.html"
        _write_text(markdown_path, render_wechat_markdown(document))
        _write_text(html_path, render_wechat_html(document))
        outputs.append(PlatformOutput(platform=Platform.WECHAT, path=markdown_path, kind="markdown"))
        outputs.append(PlatformOutput(platform=Platform.WECHAT, path=html_path, kind="html"))

    if Platform.X in platforms:
        markdown_path = target_dir / f"{stem}.x.md"
        text_path = target_dir / f"{stem}.x.txt"
        _write_text(markdown_path, render_x_markdown(document))
        _write_text(text_path, render_x_text(document))
        outputs.append(PlatformOutput(platform=Platform.X, path=markdown_path, kind="markdown"))
        outputs.append(PlatformOutput(platform=Platform.X, path=text_path, kind="text"))

    return FormatResult(outputs=outputs)


def _write_text(path: Path, content: str) -> None:
    normalized = content if content.endswith("\n") else f"{content}\n"
    path.write_text(normalized, encoding="utf-8")


def format_task_artifacts(
    task_dir: Path | str,
    *,
    platforms: list[Platform],
    source: str | None = None,
    output_dir: Path | str | None = None,
    rewrite: bool = False,
) -> FormatResult:
    task_path = Path(task_dir)
    target_dir = Path(output_dir) if output_dir is not None else task_path
    outputs: list[PlatformOutput] = []
    for platform in platforms:
        source_path = resolve_task_source(task_path, source=source, platform=platform)
        result = format_markdown_file(
            source_path,
            platforms=[platform],
            output_dir=target_dir,
            rewrite=rewrite,
        )
        outputs.extend(result.outputs)
    return FormatResult(outputs=outputs)
