import json
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import websocket

from video2post.x_fetcher import XContentFetchError

DEFAULT_BROWSER_PORT = 9223


def fetch_x_content_with_browser(url: str, *, timeout_seconds: int = 60) -> str:
    chrome_path = _find_chrome_path()
    if not chrome_path:
        raise XContentFetchError("Chrome not found. Install Google Chrome or set VIDEO2POST_CHROME_PATH.")

    port = int(os.environ.get("VIDEO2POST_CHROME_DEBUG_PORT", DEFAULT_BROWSER_PORT))
    profile_dir = Path(
        os.environ.get("VIDEO2POST_CHROME_PROFILE_DIR", Path.home() / ".video2post" / "chrome-profile")
    )
    profile_dir.mkdir(parents=True, exist_ok=True)

    chrome = _launch_chrome(chrome_path, profile_dir, port, url)
    success = False
    try:
        page_ws = _wait_for_page_websocket(port, url, timeout_seconds=timeout_seconds)
        with _CdpSession(page_ws, timeout_seconds=timeout_seconds) as cdp:
            cdp.send("Runtime.enable")
            cdp.send("Page.enable")
            current_url = str(cdp.evaluate("location.href") or "")
            if current_url != url:
                cdp.send("Page.navigate", {"url": url})
                _wait_for_ready_text(cdp, timeout_seconds=timeout_seconds, min_text_length=300)
            text = _wait_for_extractable_x_text(cdp, initial_url=url)
            success = True
            return text
    finally:
        if success and os.environ.get("VIDEO2POST_KEEP_CHROME_OPEN") != "1":
            chrome.terminate()


def _find_chrome_path() -> str | None:
    override = os.environ.get("VIDEO2POST_CHROME_PATH")
    if override and Path(override).exists():
        return override
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta",
        "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    return next((candidate for candidate in candidates if Path(candidate).exists()), None)


def _launch_chrome(chrome_path: str, profile_dir: Path, port: int, url: str) -> subprocess.Popen:
    args = [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--remote-allow-origins=http://127.0.0.1:{port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
        url,
    ]
    return subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _wait_for_page_websocket(port: int, url: str, *, timeout_seconds: int) -> str:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            pages = _list_page_targets(port)
            selected = _select_page_target(pages, url, exact_only=True)
            if selected and selected.get("webSocketDebuggerUrl"):
                return selected["webSocketDebuggerUrl"]

            request = Request(
                f"http://127.0.0.1:{port}/json/new?{quote(url, safe='')}",
                method="PUT",
            )
            with urlopen(request, timeout=5) as response:
                target = json.loads(response.read().decode("utf-8"))
            if target.get("webSocketDebuggerUrl"):
                return target["webSocketDebuggerUrl"]

            pages = _list_page_targets(port)
            selected = _select_page_target(pages, url)
            if selected and selected.get("webSocketDebuggerUrl"):
                return selected["webSocketDebuggerUrl"]
        except Exception as error:
            last_error = error
        time.sleep(0.5)
    raise XContentFetchError(f"Chrome debug port not ready: {last_error or 'no page target'}")


def _list_page_targets(port: int) -> list[dict]:
    with urlopen(f"http://127.0.0.1:{port}/json", timeout=2) as response:
        targets = json.loads(response.read().decode("utf-8"))
    return [target for target in targets if target.get("type") == "page"]


def _select_page_target(pages: list[dict], url: str, *, exact_only: bool = False) -> dict | None:
    for page in pages:
        if page.get("url", "") == url:
            return page
    if exact_only:
        return None
    for page in pages:
        page_url = page.get("url", "")
        if page_url.startswith("https://x.com/") or page_url.startswith("https://twitter.com/"):
            return page
    return pages[0] if pages else None


def _wait_for_ready_text(
    cdp: "_CdpSession",
    *,
    timeout_seconds: int,
    min_text_length: int = 20,
) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        state = cdp.evaluate("document.readyState")
        text_length = cdp.evaluate("(document.body && document.body.innerText || '').length")
        if state in {"interactive", "complete"} and int(text_length or 0) > min_text_length:
            return
        time.sleep(0.5)


def _wait_for_extractable_x_text(cdp: "_CdpSession", *, initial_url: str) -> str:
    wait_seconds = int(os.environ.get("VIDEO2POST_BROWSER_LOGIN_WAIT_SECONDS", "180"))
    deadline = time.time() + wait_seconds
    last_error = ""
    navigated_article_url = ""
    while time.time() < deadline:
        try:
            text = _extract_visible_x_text(cdp)
            if text:
                return text
        except XContentFetchError as error:
            last_error = str(error)
            article_url = _extract_article_url(cdp)
            if article_url and article_url != initial_url and article_url != navigated_article_url:
                navigated_article_url = article_url
                cdp.send("Page.navigate", {"url": article_url})
                _wait_for_ready_text(cdp, timeout_seconds=30, min_text_length=300)
        time.sleep(3)
    raise XContentFetchError(
        last_error
        or "Could not extract X content with browser. Log in to X in the opened Chrome window and retry."
    )


def _extract_article_url(cdp: "_CdpSession") -> str:
    script = """
(() => {
  const links = Array.from(document.querySelectorAll('a[href*="/i/article/"], a[href*="/article/"]'))
    .map(a => new URL(a.getAttribute('href'), location.href).href);
  return links[0] || '';
})()
"""
    return str(cdp.evaluate(script) or "").strip()


def _extract_visible_x_text(cdp: "_CdpSession") -> str:
    script = """
(() => {
  const roots = [
    document.querySelector('article'),
    document.querySelector('[data-testid="primaryColumn"]'),
    document.querySelector('main'),
    document.body
  ].filter(Boolean);
  const text = (roots[0]?.innerText || '').split('\n')
    .map(line => line.trim())
    .filter(line => line && !['Post', 'Reply', 'Repost', 'Like', 'Share', 'Search'].includes(line))
    .join('\n');
  return text;
})()
"""
    text = str(cdp.evaluate(script) or "").strip()
    if len(text) < 20 or "Log in" in text[:200]:
        raise XContentFetchError(
            "Could not extract X content with browser. Log in to X in the opened Chrome window and retry."
        )
    return text


class _CdpSession:
    def __init__(self, websocket_url: str, *, timeout_seconds: int) -> None:
        self._ws = websocket.create_connection(websocket_url, timeout=timeout_seconds)
        self._next_id = 1

    def __enter__(self) -> "_CdpSession":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._ws.close()

    def send(self, method: str, params: dict | None = None):
        message_id = self._next_id
        self._next_id += 1
        self._ws.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
        while True:
            message = json.loads(self._ws.recv())
            if message.get("id") == message_id:
                if "error" in message:
                    raise XContentFetchError(f"Chrome CDP error: {message['error']}")
                return message.get("result", {})

    def evaluate(self, expression: str):
        result = self.send(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        return result.get("result", {}).get("value")
