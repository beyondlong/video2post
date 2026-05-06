from video2post.formatters.links import LinkCollector
from video2post.formatters.markdown_parser import parse_markdown
from video2post.formatters.wechat import render_wechat_html, render_wechat_markdown


def test_link_collector_moves_external_links_to_references():
    collector = LinkCollector()

    rendered = collector.render_wechat_markdown(
        "Read [OpenAI](https://openai.com) and [WeChat](https://mp.weixin.qq.com/test)."
    )

    assert "OpenAI[1]" in rendered
    assert "[WeChat](https://mp.weixin.qq.com/test)" in rendered
    assert collector.references == [("OpenAI", "https://openai.com")]


def test_render_wechat_markdown_adds_reference_links():
    document = parse_markdown(
        """# Title

Read [OpenAI](https://openai.com).

```python
print("hi")
```
"""
    )

    output = render_wechat_markdown(document)

    assert "# Title" in output
    assert "OpenAI[1]" in output
    assert "```python" in output
    assert "## 引用链接" in output
    assert "[1] OpenAI: https://openai.com" in output


def test_render_wechat_html_uses_inline_technical_article_style():
    document = parse_markdown(
        """# Title

> Key idea

```python
print("hi")
```

Read [OpenAI](https://openai.com).
"""
    )

    html = render_wechat_html(document)

    assert '<section style="' in html
    assert "font-size: 16px" in html
    assert "line-height" in html
    assert "<h1" in html
    assert "提示" in html
    assert "<blockquote" not in html
    assert "<pre" in html
    assert "引用链接" in html
    assert "https://openai.com" in html


def test_render_wechat_html_has_tech_blogger_visual_rhythm():
    document = parse_markdown(
        """# AI Coding Workflow

## Why it matters

> The key idea is feedback speed.

```python
print("ship")
```

Read [OpenAI](https://openai.com).
"""
    )

    html = render_wechat_html(document)

    assert "技术长文" not in html
    assert "把复杂问题拆开" not in html
    assert "border-bottom: 1px solid #eadfce" in html
    assert "background: #111827" not in html
    assert "提示" in html
    assert "Python" in html
    assert "引用链接" in html
    assert "延伸阅读" in html


def test_render_wechat_html_uses_soft_engineer_blog_style():
    document = parse_markdown(
        """# 国密 TLS / TLCP 研发说明文档

## 核心结论

| 类型 | 本质 | 场景 |
|---|---|---|
| TLCP | 双证书国密协议 | 密评 |

```
1. 确认协议类型
2. 确认证书形态
```
"""
    )

    html = render_wechat_html(document)

    assert "把复杂问题拆开" not in html
    assert "技术长文" not in html
    assert "background: #111827" not in html
    assert "border-left: 4px solid #b86b2b" in html
    assert "<table" in html
    assert "TLCP" in html
    assert "清单" in html
    assert "Text" not in html
    assert "#fbf7ef" in html
    assert "#eadfce" in html
    assert "#b86b2b" in html
    assert "#2563eb" not in html
    assert "#f8fafc" not in html


def test_render_wechat_html_treats_text_fences_as_content_cards():
    document = parse_markdown(
        """# Title

```text
1. Confirm protocol type
2. Confirm certificate shape
```

```java
System.out.println(\"ship\");
```
"""
    )

    html = render_wechat_html(document)

    assert "清单" in html
    assert "Text" not in html
    assert "Java" in html
    assert "<pre" in html
