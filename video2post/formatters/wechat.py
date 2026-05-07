import html
import re

from video2post.formatters.links import LinkCollector, markdown_inline_to_html
from video2post.formatters.models import MarkdownBlock, MarkdownDocument


_THEME = {
    "text": "#2f2a24",
    "muted_text": "#6f6254",
    "heading": "#1f1b16",
    "accent": "#b86b2b",
    "accent_dark": "#8f4f1f",
    "soft_bg": "#fbf7ef",
    "panel_bg": "#f7f1e7",
    "code_bg": "#f5efe5",
    "border": "#eadfce",
}
_BODY_STYLE = (
    f"font-size: 16px; line-height: 1.82; color: {_THEME['text']}; "
    "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; "
    "letter-spacing: 0;"
)
_ORDERED_LINE_RE = re.compile(r"^\s*\d+[.)]\s+.+")
_CHECK_LINE_RE = re.compile(r"^\s*\[[ xX]\]\s+.+")
_TEXT_LIKE_LANGUAGES = {"text", "plain", "plaintext", "txt"}


def render_wechat_markdown(document: MarkdownDocument) -> str:
    collector = LinkCollector()
    parts: list[str] = []
    for block in document.blocks:
        rendered = _render_markdown_block(block, collector)
        if rendered:
            parts.append(rendered)
    if collector.references:
        parts.append(_render_markdown_references(collector.references))
    return "\n\n".join(parts).rstrip() + "\n"


def render_wechat_html(document: MarkdownDocument) -> str:
    collector = LinkCollector()
    title = _document_title(document)
    parts = [f'<section style="{_BODY_STYLE}">']
    if title:
        parts.append(_render_article_header(title))
    for block in document.blocks:
        if block.kind == "heading" and block.level == 1 and block.text == title:
            continue
        rendered = _render_html_block(block, collector)
        if rendered:
            parts.append(rendered)
    if collector.references:
        parts.append(_render_html_references(collector.references))
    parts.append("</section>")
    return "\n".join(parts) + "\n"


def _document_title(document: MarkdownDocument) -> str:
    for block in document.blocks:
        if block.kind == "heading" and block.level == 1:
            return block.text
    return ""


def _render_article_header(title: str) -> str:
    return (
        '<section style="margin: 0 0 2em; padding: 0 0 1.15em; '
        f'border-bottom: 1px solid {_THEME["border"]};">'
        '<h1 style="font-size: 25px; line-height: 1.38; font-weight: 800; '
        f'margin: 0; color: {_THEME["heading"]};">'
        f'{html.escape(title)}</h1>'
        '</section>'
    )


def _render_markdown_block(block: MarkdownBlock, collector: LinkCollector) -> str:
    if block.kind == "heading":
        level = block.level or 1
        return f"{'#' * level} {block.text}"
    if block.kind == "paragraph":
        return collector.render_wechat_markdown(block.text)
    if block.kind == "blockquote":
        return "\n".join(f"> {line}" for line in block.text.splitlines())
    if block.kind == "unordered_list":
        return "\n".join(f"- {collector.render_wechat_markdown(item)}" for item in block.items)
    if block.kind == "ordered_list":
        return "\n".join(
            f"{index}. {collector.render_wechat_markdown(item)}"
            for index, item in enumerate(block.items, start=1)
        )
    if block.kind == "code_block":
        language = block.language or ""
        return f"```{language}\n{block.text}\n```"
    if block.kind == "table":
        lines = ["| " + " | ".join(block.headers) + " |"]
        lines.append("|" + "|".join("---" for _ in block.headers) + "|")
        lines.extend("| " + " | ".join(row) + " |" for row in block.rows)
        return "\n".join(lines)
    if block.kind == "horizontal_rule":
        return "---"
    return block.text


def _render_markdown_references(references: list[tuple[str, str]]) -> str:
    lines = ["## 引用链接", ""]
    lines.extend(f"[{index}] {label}: {url}" for index, (label, url) in enumerate(references, start=1))
    return "\n".join(lines)


def _render_html_block(block: MarkdownBlock, collector: LinkCollector) -> str:
    if block.kind == "heading":
        level = min(max(block.level or 1, 1), 6)
        text = html.escape(block.text)
        if level == 1:
            return _render_article_header(block.text)
        if level == 2:
            return (
                '<section style="margin: 2em 0 1em; padding: 0.75em 0.9em; '
                f'background: {_THEME["soft_bg"]}; border-left: 4px solid {_THEME["accent"]}; '
                'border-radius: 0 6px 6px 0;">'
                '<h2 style="font-size: 19px; font-weight: 800; line-height: 1.45; '
                f'margin: 0; color: {_THEME["heading"]};">'
                f'{text}</h2></section>'
            )
        style = (
            "font-size: 17px; font-weight: 800; margin: 1.45em 0 0.75em; "
            f"color: {_THEME['heading']};"
        )
        return f'<h{level} style="{style}">{text}</h{level}>'
    if block.kind == "paragraph":
        return (
            f'<p style="margin: 0 0 1.05em; color: {_THEME["text"]};">'
            f'{collector.render_wechat_html(block.text)}</p>'
        )
    if block.kind == "blockquote":
        label, text = _split_note_label(block.text)
        return _render_note_card(label, text)
    if block.kind == "unordered_list":
        items = "".join(
            f'<li style="margin: 0.38em 0; padding-left: 0.1em;">{collector.render_wechat_html(item)}</li>'
            for item in block.items
        )
        return f'<ul style="margin: 0 0 1.1em 1.2em; padding: 0; color: {_THEME["muted_text"]};">{items}</ul>'
    if block.kind == "ordered_list":
        items = "".join(
            f'<li style="margin: 0.38em 0; padding-left: 0.1em;">{collector.render_wechat_html(item)}</li>'
            for item in block.items
        )
        return f'<ol style="margin: 0 0 1.1em 1.2em; padding: 0; color: {_THEME["muted_text"]};">{items}</ol>'
    if block.kind == "table":
        return _render_table(block, collector)
    if block.kind == "code_block":
        return _render_code_or_card(block)
    if block.kind == "horizontal_rule":
        return f'<hr style="border: 0; border-top: 1px dashed {_THEME["border"]}; margin: 1.8em 0;" />'
    return f'<p style="margin: 0 0 1.05em;">{markdown_inline_to_html(block.text)}</p>'


def _render_code_or_card(block: MarkdownBlock) -> str:
    language = (block.language or "").strip().lower()
    if language and language not in _TEXT_LIKE_LANGUAGES:
        return _render_code_block(block.text, block.language or "")
    label = _card_label(block.text)
    return _render_note_card(label, block.text)


def _card_label(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines and all(_ORDERED_LINE_RE.match(line) or _CHECK_LINE_RE.match(line) for line in lines):
        return "清单"
    if any("=" in line or "=>" in line or "->" in line for line in lines):
        return "要点"
    return "说明"



def _split_note_label(text: str) -> tuple[str, str]:
    match = re.match(r"^(说明|要点|清单)[:：]\s*(.+)$", text.strip(), flags=re.S)
    if match:
        return match.group(1), match.group(2)
    return "提示", text

def _render_note_card(label: str, text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    body = "<br />".join(html.escape(line) for line in lines) or html.escape(text)
    return (
        '<section style="margin: 1.25em 0; padding: 1em 1.05em; '
        f'background: {_THEME["soft_bg"]}; border: 1px solid {_THEME["border"]}; '
        f'border-left: 4px solid {_THEME["accent"]}; border-radius: 8px;">'
        f'<p style="margin: 0 0 0.55em; font-size: 13px; font-weight: 700; color: {_THEME["accent_dark"]};">'
        f'{html.escape(label)}</p>'
        f'<p style="margin: 0; color: {_THEME["muted_text"]}; line-height: 1.75;">{body}</p></section>'
    )


def _render_code_block(text: str, language: str) -> str:
    code = html.escape(text)
    language_label = language.strip().capitalize()
    return (
        f'<section style="margin: 1.35em 0; border: 1px solid {_THEME["border"]}; '
        f'border-radius: 8px; overflow: hidden; background: {_THEME["code_bg"]};">'
        f'<p style="margin: 0; padding: 0.45em 0.8em; background: {_THEME["panel_bg"]}; '
        f'font-size: 13px; color: {_THEME["muted_text"]}; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;">'
        f'{html.escape(language_label)}</p>'
        f'<pre style="margin: 0; padding: 1em; background: {_THEME["code_bg"]}; overflow-x: auto; '
        'white-space: pre-wrap; overflow-wrap: break-word; font-size: 14px; line-height: 1.65;">'
        f'<code>{code}</code></pre></section>'
    )


def _render_table(block: MarkdownBlock, collector: LinkCollector) -> str:
    headers = "".join(
        f'<th style="padding: 0.65em 0.7em; background: {_THEME["panel_bg"]}; color: {_THEME["heading"]}; '
        f'font-weight: 700; border: 1px solid {_THEME["border"]}; text-align: left;">'
        f'{collector.render_wechat_html(header)}</th>'
        for header in block.headers
    )
    rows = []
    for row in block.rows:
        cells = "".join(
            f'<td style="padding: 0.65em 0.7em; border: 1px solid {_THEME["border"]}; '
            f'vertical-align: top; color: {_THEME["muted_text"]};">'
            f'{collector.render_wechat_html(cell)}</td>'
            for cell in row
        )
        rows.append(f"<tr>{cells}</tr>")
    return (
        '<section style="margin: 1.25em 0; overflow-x: auto;">'
        '<table style="border-collapse: collapse; width: 100%; font-size: 14px; line-height: 1.65;">'
        f'<thead><tr>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></section>'
    )


def _render_html_references(references: list[tuple[str, str]]) -> str:
    items = []
    for index, (label, url) in enumerate(references, start=1):
        items.append(
            f'<p style="margin: 0.45em 0; font-size: 14px; color: {_THEME["muted_text"]}; line-height: 1.65;">'
            f'<span style="font-weight: 700; color: {_THEME["accent_dark"]};">[{index}]</span> '
            f'{html.escape(label)}：{html.escape(url)}</p>'
        )
    return (
        '<section style="margin-top: 2em; padding: 1em 1em 0.8em; '
        f'background: {_THEME["soft_bg"]}; border-radius: 8px; border: 1px solid {_THEME["border"]};">'
        f'<p style="margin: 0 0 0.25em; font-size: 13px; color: {_THEME["accent_dark"]}; font-weight: 700;">延伸阅读</p>'
        f'<h2 style="font-size: 17px; margin: 0 0 0.8em; color: {_THEME["heading"]};">引用链接</h2>'
        + "".join(items)
        + "</section>"
    )
