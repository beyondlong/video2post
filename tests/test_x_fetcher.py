import httpx

from video2post.x_fetcher import XContentFetchError, fetch_x_content, is_x_status_url


class FakeResponse:
    def __init__(self, payload, status_code=200, text=None, url="https://publish.x.com/oembed"):
        self.payload = payload
        self.status_code = status_code
        self.text = text if text is not None else ""
        self.url = url

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", self.url)
            response = httpx.Response(self.status_code, request=request, text="not found")
            raise httpx.HTTPStatusError("failed", request=request, response=response)

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def get(self, url, *, params=None, timeout):
        self.requests.append({"url": url, "params": params, "timeout": timeout})
        if isinstance(self.response, dict):
            return self.response[url]
        return self.response


def test_is_x_status_url_accepts_x_and_twitter_status_links():
    assert is_x_status_url("https://x.com/user/status/123")
    assert is_x_status_url("https://twitter.com/user/status/123")
    assert not is_x_status_url("https://example.com/user/status/123")


def test_fetch_x_content_extracts_tweet_text_from_oembed_html():
    html = (
        '<blockquote class="twitter-tweet">'
        '<p lang="zh" dir="ltr">真正拉开差距的不是工具，而是反馈速度。'
        '<a href="https://t.co/abc">pic.twitter.com/abc</a></p>'
        '&mdash; 张三 (@zhangsan) <a href="https://x.com/zhangsan/status/123">May 11, 2026</a>'
        '</blockquote>'
    )
    client = FakeHttpClient(FakeResponse({"html": html}))

    content = fetch_x_content("https://x.com/zhangsan/status/123", http_client=client)

    assert content == "真正拉开差距的不是工具，而是反馈速度。"
    assert client.requests[0]["url"] == "https://publish.x.com/oembed"
    assert client.requests[0]["params"]["url"] == "https://x.com/zhangsan/status/123"
    assert client.requests[0]["params"]["omit_script"] == "1"


def test_fetch_x_content_raises_for_non_x_status_url():
    try:
        fetch_x_content("https://example.com/post/1", http_client=FakeHttpClient(FakeResponse({})))
    except ValueError as error:
        assert "Expected an X/Twitter status URL" in str(error)
    else:
        raise AssertionError("Expected non-X URL to fail")


def test_fetch_x_content_raises_when_oembed_has_no_text():
    client = FakeHttpClient(FakeResponse({"html": "<blockquote></blockquote>"}))

    try:
        fetch_x_content("https://x.com/user/status/123", http_client=client)
    except XContentFetchError as error:
        assert "Could not extract tweet text" in str(error)
    else:
        raise AssertionError("Expected empty oEmbed response to fail")


def test_fetch_x_content_removes_short_links_from_text():
    html = (
        '<blockquote class="twitter-tweet">'
        '<p lang="zh" dir="ltr">这篇文章讲透了 AI 产品的关键。'
        '<a href="https://t.co/IYuqDZ5lxi">https://t.co/IYuqDZ5lxi</a></p>'
        '&mdash; 张三 (@zhangsan)'
        '</blockquote>'
    )
    client = FakeHttpClient(FakeResponse({"html": html}))

    content = fetch_x_content("https://x.com/zhangsan/status/123", http_client=client)

    assert content == "这篇文章讲透了 AI 产品的关键。"


def test_fetch_x_content_follows_link_only_tweet_to_article():
    html = (
        '<blockquote class="twitter-tweet">'
        '<p lang="zxx" dir="ltr">'
        '<a href="https://t.co/IYuqDZ5lxi">https://t.co/IYuqDZ5lxi</a></p>'
        '&mdash; 张三 (@zhangsan)'
        '</blockquote>'
    )
    article_html = (
        '<html><head><title>AI 产品思考</title>'
        '<meta name="description" content="文章摘要说明。"></head>'
        '<body><p>第一段正文足够长，说明这篇文章真正讨论了 AI 产品和反馈速度。</p>'
        '<p>第二段正文继续展开，适合提炼成 X 内容。</p></body></html>'
    )
    client = FakeHttpClient({
        "https://publish.x.com/oembed": FakeResponse({"html": html}),
        "https://t.co/IYuqDZ5lxi": FakeResponse({}, text=article_html, url="https://example.com/article"),
    })

    content = fetch_x_content("https://x.com/zhangsan/status/123", http_client=client)

    assert "AI 产品思考" in content
    assert "第一段正文足够长" in content
    assert client.requests[1]["url"] == "https://t.co/IYuqDZ5lxi"


def test_fetch_x_content_rejects_link_only_tweet_when_link_page_has_no_text():
    html = (
        '<blockquote class="twitter-tweet">'
        '<p lang="zxx" dir="ltr">'
        '<a href="https://t.co/IYuqDZ5lxi">https://t.co/IYuqDZ5lxi</a></p>'
        '&mdash; 张三 (@zhangsan)'
        '</blockquote>'
    )
    client = FakeHttpClient(FakeResponse({"html": html}))

    try:
        fetch_x_content("https://x.com/zhangsan/status/123", http_client=client)
    except XContentFetchError as error:
        assert "only links or media" in str(error)
    else:
        raise AssertionError("Expected link-only tweet to fail")
