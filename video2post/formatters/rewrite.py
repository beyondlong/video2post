from pathlib import Path

from video2post.config import AppConfig, load_config
from video2post.formatters.models import Platform
from video2post.llm.openai_compatible import OpenAICompatibleProvider
from video2post.llm.prompts import PromptRenderer


def rewrite_markdown(
    content: str,
    platforms: list[Platform],
    *,
    config: AppConfig | None = None,
    provider: object | None = None,
    prompt_dir: Path | str = "prompts",
) -> str:
    active_config = config or load_config(None)
    active_provider = provider or OpenAICompatibleProvider(settings=active_config.llm)
    renderer = PromptRenderer(prompt_dir)
    prompt = renderer.render(
        "format_rewrite",
        {
            "platforms": ",".join(platform.value for platform in platforms),
            "markdown": content,
        },
    )
    rewritten = active_provider.generate(prompt).strip()
    if not rewritten:
        raise RuntimeError("LLM rewrite returned empty content.")
    return rewritten
