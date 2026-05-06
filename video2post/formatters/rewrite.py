from video2post.formatters.models import Platform


def rewrite_markdown(content: str, platforms: list[Platform]) -> str:
    raise RuntimeError(
        "Markdown rewrite is not implemented yet. Run without --rewrite for deterministic formatting."
    )
