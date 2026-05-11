import httpx

from video2post.x_fetcher import XContentFetchError, fetch_x_content, is_x_status_url


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://publish.x.com/oembed")
            response = httpx.Response(self.status_code, request=request, text="not found")
            raise httpx.HTTPStatusError("failed", request=request, response=response)

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def get(self, url, *, params, timeout):
        self.requests.append({"url": url, "params": params, "timeout": timeout})
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

    assert content == "真正拉开差距的不是工具，而是反馈速度。 pic.twitter.com/abc"
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
