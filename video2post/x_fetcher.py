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

    text = _extract_tweet_text(html)
    if not text:
        raise XContentFetchError("Could not extract tweet text from X oEmbed response.")
    return text


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
