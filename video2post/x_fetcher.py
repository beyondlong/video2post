import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

OEMBED_URL = "https://publish.x.com/oembed"


class XContentFetchError(RuntimeError):
    pass


def is_x_status_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value.strip())
    hostname = (parsed.hostname or "").lower()
    if hostname not in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}:
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return len(parts) >= 3 and parts[1] == "status" and parts[2].isdigit()


def fetch_x_content(
    url: str,
    *,
    http_client: object | None = None,
    timeout_seconds: int = 30,
) -> str:
    if not is_x_status_url(url):
        raise ValueError("Expected an X/Twitter status URL.")

    client = http_client or httpx.Client(follow_redirects=True)
    try:
        response = client.get(
            OEMBED_URL,
            params={
                "url": url,
                "omit_script": "1",
                "hide_thread": "0",
                "hide_media": "0",
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as error:
        raise XContentFetchError(f"Could not fetch X content: {error}") from error
    except ValueError as error:
        raise XContentFetchError("Could not parse X oEmbed response as JSON.") from error

    html = payload.get("html") if isinstance(payload, dict) else None
    if not isinstance(html, str):
        raise XContentFetchError("Could not extract tweet text from X oEmbed response.")

    raw_text = _extract_tweet_text(html)
    if not raw_text:
        raise XContentFetchError("Could not extract tweet text from X oEmbed response.")
    if _is_link_only_text(raw_text):
        linked_content = _fetch_linked_content_from_tweet(
            html,
            client=client,
            timeout_seconds=timeout_seconds,
        )
        if linked_content:
            return linked_content
        raise XContentFetchError(
            "X post contains only links or media; paste the linked article or tweet text instead."
        )
    text = _clean_tweet_text(raw_text)
    if not text:
        raise XContentFetchError("Could not extract tweet text from X oEmbed response.")
    return text



def _fetch_linked_content_from_tweet(
    html: str,
    *,
    client: object,
    timeout_seconds: int,
) -> str:
    for link in _extract_tweet_links(html):
        if not _is_external_content_link(link):
            continue
        try:
            response = client.get(link, params=None, timeout=timeout_seconds)
            response.raise_for_status()
        except (httpx.HTTPError, ValueError):
            continue
        page_text = _extract_page_text(getattr(response, "text", ""))
        if page_text:
            return page_text
    return ""


def _extract_tweet_links(html: str) -> list[str]:
    parser = _TweetLinkParser()
    parser.feed(html)
    return parser.links()


def _is_external_content_link(link: str) -> bool:
    parsed = urlparse(link)
    if parsed.scheme not in {"http", "https"}:
        return False
    hostname = (parsed.hostname or "").lower()
    if hostname in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}:
        return False
    if hostname.endswith("twimg.com") or hostname in {"pic.twitter.com", "twitter.com"}:
        return False
    return True


def _extract_page_text(html: str) -> str:
    if not html.strip():
        return ""
    parser = _PageTextParser()
    parser.feed(html)
    return parser.text()


def _clean_tweet_text(text: str) -> str:
    cleaned = re.sub(r"https?://\S+", " ", text)
    cleaned = re.sub(r"(?:pic\.)?twitter\.com/\S+", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"t\.co/\S+", " ", cleaned, flags=re.IGNORECASE)
    return " ".join(cleaned.split())


def _is_link_only_text(text: str) -> bool:
    compact = _clean_tweet_text(text)
    if not compact:
        return True
    meaningful = re.sub(r"[\W_]+", "", compact, flags=re.UNICODE)
    return len(meaningful) < 4


def _extract_tweet_text(html: str) -> str:
    parser = _TweetParagraphParser()
    parser.feed(html)
    text = parser.text()
    if text:
        return text

    fallback = _strip_html_text(html)
    if "—" in fallback:
        fallback = fallback.split("—", 1)[0]
    return " ".join(fallback.split())


def _strip_html_text(html: str) -> str:
    parser = _AllTextParser()
    parser.feed(html)
    return parser.text()


class _TweetLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._links: list[str] = []
        self._in_first_paragraph = False
        self._seen_paragraph = False

    def handle_starttag(self, tag: str, attrs) -> None:
        tag_name = tag.lower()
        if tag_name == "p" and not self._seen_paragraph:
            self._in_first_paragraph = True
            self._seen_paragraph = True
            return
        if tag_name == "a" and self._in_first_paragraph:
            href = dict(attrs).get("href")
            if href:
                self._links.append(href.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "p" and self._in_first_paragraph:
            self._in_first_paragraph = False

    def links(self) -> list[str]:
        seen: set[str] = set()
        links: list[str] = []
        for link in self._links:
            if link and link not in seen:
                seen.add(link)
                links.append(link)
        return links


class _PageTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._title_parts: list[str] = []
        self._description = ""
        self._paragraphs: list[str] = []
        self._current_paragraph: list[str] = []
        self._in_title = False
        self._in_paragraph = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        tag_name = tag.lower()
        if tag_name in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        attrs_dict = {name.lower(): value for name, value in attrs}
        if tag_name == "title":
            self._in_title = True
        elif tag_name == "meta":
            name = (attrs_dict.get("name") or attrs_dict.get("property") or "").lower()
            if name in {"description", "og:description", "twitter:description"}:
                self._description = attrs_dict.get("content", "").strip()
        elif tag_name == "p":
            self._in_paragraph = True
            self._current_paragraph = []

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        if tag_name in {"script", "style", "noscript"}:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag_name == "title":
            self._in_title = False
        elif tag_name == "p" and self._in_paragraph:
            paragraph = " ".join(" ".join(self._current_paragraph).split())
            if paragraph:
                self._paragraphs.append(paragraph)
            self._current_paragraph = []
            self._in_paragraph = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self._title_parts.append(data)
        elif self._in_paragraph:
            self._current_paragraph.append(data)

    def text(self) -> str:
        title = " ".join(" ".join(self._title_parts).split())
        parts = [part for part in [title, self._description, *self._paragraphs] if part]
        text = "\n\n".join(parts)
        return text[:12000].strip()


class _TweetParagraphParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_paragraph = False
        self._seen_paragraph = False
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "p" and not self._seen_paragraph:
            self._in_paragraph = True
            self._seen_paragraph = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "p" and self._in_paragraph:
            self._in_paragraph = False

    def handle_data(self, data: str) -> None:
        if self._in_paragraph:
            self._parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self._parts).split())


class _AllTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self._parts).split())
