import html
import re

_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")


class LinkCollector:
    def __init__(self) -> None:
        self.references: list[tuple[str, str]] = []

    def render_wechat_markdown(self, text: str) -> str:
        return _LINK_RE.sub(self._wechat_markdown_link, text)

    def render_wechat_html(self, text: str) -> str:
        escaped = markdown_inline_to_html(text, link_renderer=self._wechat_html_link)
        return escaped

    def _wechat_markdown_link(self, match: re.Match[str]) -> str:
        label = match.group(1)
        url = match.group(2)
        if _is_wechat_url(url):
            return match.group(0)
        self.references.append((label, url))
        return f"{label}[{len(self.references)}]"

    def _wechat_html_link(self, label: str, url: str) -> str:
        if _is_wechat_url(url):
            return (
                f'<a href="{html.escape(url, quote=True)}" '
                'style="color: #2563eb; text-decoration: none;">'
                f"{html.escape(label)}</a>"
            )
        self.references.append((label, url))
        return f"{html.escape(label)}<sup>[{len(self.references)}]</sup>"


def markdown_inline_to_plain_text(text: str) -> str:
    text = _IMAGE_RE.sub(lambda match: match.group(1), text)
    text = _LINK_RE.sub(lambda match: f"{match.group(1)}: {match.group(2)}", text)
    text = _CODE_RE.sub(lambda match: match.group(1), text)
    text = _BOLD_RE.sub(lambda match: match.group(1), text)
    text = _ITALIC_RE.sub(lambda match: match.group(1), text)
    return text


def markdown_inline_to_html(
    text: str,
    *,
    link_renderer: object | None = None,
) -> str:
    image_placeholders: list[str] = []

    def store_image(match: re.Match[str]) -> str:
        alt = html.escape(match.group(1), quote=True)
        src = html.escape(match.group(2), quote=True)
        rendered = (
            f'<img src="{src}" alt="{alt}" '
            'style="max-width: 100%; height: auto; display: block; margin: 1em auto;" />'
        )
        image_placeholders.append(rendered)
        return f"\u0000IMG{len(image_placeholders) - 1}\u0000"

    text = _IMAGE_RE.sub(store_image, text)
    escaped = html.escape(text)

    def replace_link(match: re.Match[str]) -> str:
        label = html.unescape(match.group(1))
        url = html.unescape(match.group(2))
        if link_renderer is not None:
            return link_renderer(label, url)  # type: ignore[misc]
        return (
            f'<a href="{html.escape(url, quote=True)}" '
            'style="color: #2563eb; text-decoration: none;">'
            f"{html.escape(label)}</a>"
        )

    escaped = _LINK_RE.sub(replace_link, escaped)
    escaped = _CODE_RE.sub(lambda match: f"<code>{match.group(1)}</code>", escaped)
    escaped = _BOLD_RE.sub(lambda match: f"<strong>{match.group(1)}</strong>", escaped)
    escaped = _ITALIC_RE.sub(lambda match: f"<em>{match.group(1)}</em>", escaped)
    for index, rendered in enumerate(image_placeholders):
        escaped = escaped.replace(f"\u0000IMG{index}\u0000", rendered)
    return escaped


def _is_wechat_url(url: str) -> bool:
    return url.startswith("https://mp.weixin.qq.com/") or url.startswith("http://mp.weixin.qq.com/")
