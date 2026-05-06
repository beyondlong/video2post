import re

from video2post.formatters.links import markdown_inline_to_plain_text
from video2post.formatters.models import MarkdownBlock, MarkdownDocument


_ORDERED_LINE_RE = re.compile(r"^\s*\d+[.)]\s+.+")
_CHECK_LINE_RE = re.compile(r"^\s*\[[ xX]\]\s+.+")
_TEXT_LIKE_LANGUAGES = {"text", "plain", "plaintext", "txt"}


def render_x_markdown(document: MarkdownDocument) -> str:
    parts: list[str] = []
    for block in document.blocks:
        rendered = _render_markdown_block(block)
        if rendered:
            parts.append(rendered)
    return "\n\n".join(parts).rstrip() + "\n"


def render_x_text(document: MarkdownDocument) -> str:
    parts: list[str] = []
    for block in document.blocks:
        rendered = _render_text_block(block)
        if rendered:
            parts.append(rendered)
    return "\n\n".join(parts).rstrip() + "\n"


def _render_markdown_block(block: MarkdownBlock) -> str:
    if block.kind == "heading":
        return f"{'#' * (block.level or 1)} {block.text}"
    if block.kind == "paragraph":
        return block.text
    if block.kind == "blockquote":
        return _render_markdown_content_card("提示", block.text)
    if block.kind == "unordered_list":
        return "\n".join(f"- {item}" for item in block.items)
    if block.kind == "ordered_list":
        return "\n".join(f"{index}. {item}" for index, item in enumerate(block.items, start=1))
    if block.kind == "code_block":
        return _render_markdown_code_or_card(block)
    if block.kind == "table":
        return _render_markdown_table(block)
    if block.kind == "horizontal_rule":
        return "---"
    return block.text


def _render_text_block(block: MarkdownBlock) -> str:
    if block.kind == "heading":
        text = markdown_inline_to_plain_text(block.text)
        if block.level == 1:
            return f"{text}\n{'=' * len(text)}"
        return text
    if block.kind == "paragraph":
        return markdown_inline_to_plain_text(block.text)
    if block.kind == "blockquote":
        return _render_text_content_card("提示", block.text)
    if block.kind == "unordered_list":
        return "\n".join(f"• {markdown_inline_to_plain_text(item)}" for item in block.items)
    if block.kind == "ordered_list":
        return "\n".join(
            f"{index}. {markdown_inline_to_plain_text(item)}"
            for index, item in enumerate(block.items, start=1)
        )
    if block.kind == "code_block":
        return _render_text_code_or_card(block)
    if block.kind == "table":
        return _render_text_table(block)
    if block.kind == "horizontal_rule":
        return ""
    return markdown_inline_to_plain_text(block.text)


def _render_markdown_code_or_card(block: MarkdownBlock) -> str:
    language = (block.language or "").strip().lower()
    if language and language not in _TEXT_LIKE_LANGUAGES:
        return f"```{block.language or ''}\n{block.text}\n```"
    return _render_markdown_content_card(_card_label(block.text), block.text)


def _render_text_code_or_card(block: MarkdownBlock) -> str:
    language = (block.language or "").strip().lower()
    if language and language not in _TEXT_LIKE_LANGUAGES:
        label = block.language.strip() if block.language else "code"
        return f"[{label}]\n{block.text}"
    return _render_text_content_card(_card_label(block.text), block.text)


def _card_label(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines and all(_ORDERED_LINE_RE.match(line) or _CHECK_LINE_RE.match(line) for line in lines):
        return "清单"
    if any("=" in line or "=>" in line or "->" in line for line in lines):
        return "要点"
    return "说明"


def _render_markdown_content_card(label: str, text: str) -> str:
    lines = [markdown_inline_to_plain_text(line.strip()) for line in text.splitlines() if line.strip()]
    body = lines or [markdown_inline_to_plain_text(text)]
    return "\n".join([f"> **{label}**", ">"] + [f"> {line}" for line in body])


def _render_text_content_card(label: str, text: str) -> str:
    lines = [markdown_inline_to_plain_text(line.strip()) for line in text.splitlines() if line.strip()]
    body = lines or [markdown_inline_to_plain_text(text)]
    return "\n".join([f"【{label}】"] + body)


def _render_markdown_table(block: MarkdownBlock) -> str:
    lines = ["| " + " | ".join(block.headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in block.headers) + " |")
    lines.extend("| " + " | ".join(row) + " |" for row in block.rows)
    return "\n".join(lines)


def _render_text_table(block: MarkdownBlock) -> str:
    if not block.headers:
        return ""
    rendered_rows = []
    for index, row in enumerate(block.rows, start=1):
        pairs = []
        for header, cell in zip(block.headers, row):
            header_text = markdown_inline_to_plain_text(header)
            cell_text = markdown_inline_to_plain_text(cell)
            pairs.append(f"{header_text}：{cell_text}")
        rendered_rows.append(f"{index}. " + "；".join(pairs))
    return "\n".join(["【表格】"] + rendered_rows)
