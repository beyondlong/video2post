import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from video2post.config import AppConfig
from video2post.llm.openai_compatible import OpenAICompatibleProvider
from video2post.llm.prompts import PromptRenderer
from video2post.writers.markdown import write_markdown

SUPPORTED_DRAFT_MODES = {"x_engage", "viral_280"}
VIRAL_280_LIMIT = 280


@dataclass
class DraftResult:
    task_dir: Path
    paths: list[Path]


def generate_draft(
    content: str,
    config: AppConfig,
    *,
    mode: str = "x_engage",
    x_url: str | None = None,
    output_dir: Path | str | None = None,
    title: str | None = None,
    provider: object | None = None,
    prompt_dir: Path | str = "prompts",
    progress_callback: Callable[[str], None] | None = None,
) -> DraftResult:
    normalized_mode = mode.strip().lower()
    if normalized_mode not in SUPPORTED_DRAFT_MODES:
        raise ValueError(f"Unsupported draft mode: {mode}. Supported modes: x_engage, viral_280.")

    normalized_content = content.strip()
    if not normalized_content:
        raise ValueError("Draft content must not be empty.")

    task_dir = _create_draft_dir(output_dir or Path("drafts"), title or normalized_content)
    generated_paths: list[Path] = []
    metadata = _new_metadata(
        task_dir=task_dir,
        mode=normalized_mode,
        content=normalized_content,
        x_url=x_url,
        title=title,
    )
    _write_draft_metadata(task_dir, metadata)

    try:
        source_path = write_markdown(task_dir / "source.md", normalized_content)
        generated_paths.append(source_path)

        active_provider = provider or OpenAICompatibleProvider(settings=config.llm)
        renderer = PromptRenderer(prompt_dir)

        _report_progress(progress_callback, "Generating draft brief...")
        brief = active_provider.generate(
            renderer.render(
                "draft_brief",
                {
                    "content": normalized_content,
                    "x_url": x_url or "",
                    "brief": "",
                },
            )
        )
        brief_path = write_markdown(task_dir / "brief.md", brief)
        generated_paths.append(brief_path)

        context = {
            "content": normalized_content,
            "brief": brief,
            "x_url": x_url or "",
        }
        if normalized_mode == "x_engage":
            generated_paths.extend(
                _generate_x_engage_outputs(task_dir, renderer, active_provider, context, progress_callback)
            )
        else:
            viral_path = _generate_viral_280_output(
                task_dir, renderer, active_provider, context, progress_callback
            )
            generated_paths.append(viral_path)

        metadata["status"] = "completed"
        metadata["llm_model"] = getattr(active_provider, "model_name", None)
        metadata["outputs"] = [path.name for path in generated_paths]
        metadata["updated_at"] = _now()
        metadata["error"] = None
        _write_draft_metadata(task_dir, metadata)
        return DraftResult(task_dir=task_dir, paths=generated_paths)
    except Exception as error:
        metadata["status"] = "failed"
        metadata["updated_at"] = _now()
        metadata["error"] = {
            "stage": "viral_280_validation"
            if "viral_280 output exceeds 280 characters" in str(error)
            else "llm_generation",
            "message": str(error),
            "retryable": True,
        }
        _write_draft_metadata(task_dir, metadata)
        raise


def _generate_x_engage_outputs(
    task_dir: Path,
    renderer: PromptRenderer,
    provider: object,
    context: dict[str, str],
    progress_callback: Callable[[str], None] | None,
) -> list[Path]:
    outputs = [
        ("x_engage_replies", "x_replies.md", "Generating X reply candidates..."),
        ("x_engage_quote", "x_quote.md", "Generating X quote candidates..."),
        ("x_engage_posts", "x_posts.md", "Generating X post candidates..."),
    ]
    paths: list[Path] = []
    for prompt_name, filename, progress in outputs:
        _report_progress(progress_callback, progress)
        content = provider.generate(renderer.render(prompt_name, context))
        paths.append(write_markdown(task_dir / filename, content))
    return paths


def _generate_viral_280_output(
    task_dir: Path,
    renderer: PromptRenderer,
    provider: object,
    context: dict[str, str],
    progress_callback: Callable[[str], None] | None,
) -> Path:
    _report_progress(progress_callback, "Generating viral_280 tweet...")
    tweet = provider.generate(renderer.render("viral_280", context)).strip()
    if len(tweet) > VIRAL_280_LIMIT:
        raise RuntimeError(
            f"viral_280 output exceeds 280 characters: {len(tweet)} characters."
        )
    return write_markdown(task_dir / "viral_280.md", tweet)


def _new_metadata(
    *,
    task_dir: Path,
    mode: str,
    content: str,
    x_url: str | None,
    title: str | None,
) -> dict:
    now = _now()
    return {
        "type": "draft",
        "mode": mode,
        "status": "created",
        "task_dir": str(task_dir),
        "title": title,
        "x_url": x_url,
        "content_chars": len(content),
        "created_at": now,
        "updated_at": now,
        "llm_model": None,
        "outputs": [],
        "error": None,
    }


def _create_draft_dir(output_dir: Path | str, seed: str) -> Path:
    root = Path(output_dir)
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    slug = _slugify(seed[:48])
    candidate = root / f"{date_prefix}-{slug}"
    if not candidate.exists():
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate

    suffix = 2
    while True:
        next_candidate = root / f"{date_prefix}-{slug}-{suffix}"
        if not next_candidate.exists():
            next_candidate.mkdir(parents=True, exist_ok=True)
            return next_candidate
        suffix += 1


def _slugify(value: str) -> str:
    normalized = value.lower()
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "-", normalized, flags=re.UNICODE).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:60] or "untitled"


def _write_draft_metadata(task_dir: Path, metadata: dict) -> Path:
    path = task_dir / "meta.json"
    path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _report_progress(progress_callback: Callable[[str], None] | None, message: str) -> None:
    if progress_callback is not None:
        progress_callback(message)
