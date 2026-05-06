from video2post.formatters.links import markdown_inline_to_plain_text
from video2post.formatters.markdown_parser import parse_markdown
from video2post.formatters.x_longform import render_x_markdown, render_x_text


def test_markdown_inline_to_plain_text_expands_links():
    text = markdown_inline_to_plain_text("Read **this** [post](https://example.com).")

    assert text == "Read this post: https://example.com."


def test_render_x_markdown_preserves_structure():
    document = parse_markdown("# Title\n\n- one\n- two\n\n[OpenAI](https://openai.com)")

    output = render_x_markdown(document)

    assert "# Title" in output
    assert "- one" in output
    assert "[OpenAI](https://openai.com)" in output


def test_render_x_text_strips_noisy_markdown():
    document = parse_markdown("# Title\n\nRead **this** [post](https://example.com).")

    output = render_x_text(document)

    assert "Title" in output
    assert "**" not in output
    assert "post: https://example.com" in output


def test_render_x_text_has_longform_publishing_rhythm():
    document = parse_markdown(
        """# AI Coding Workflow

> The key idea is feedback speed.

- one
- two

Read **this** [post](https://example.com).
"""
    )

    output = render_x_text(document)

    assert output.startswith("AI Coding Workflow\n" + "=" * len("AI Coding Workflow"))
    assert "【提示】" in output
    assert "The key idea is feedback speed." in output
    assert "• one" in output
    assert "• two" in output
    assert "Read this post: https://example.com." in output


def test_render_x_markdown_uses_content_cards_for_text_fences_and_tables():
    document = parse_markdown(
        """# Title

```text
A = B
C = D
```

```python
print("ship")
```

| Type | Meaning |
|---|---|
| TLCP | 双证书国密协议 |
"""
    )

    output = render_x_markdown(document)

    assert "> **要点**" in output
    assert "> A = B" in output
    assert "```text" not in output
    assert "```python" in output
    assert "| Type | Meaning |" in output
    assert "| TLCP | 双证书国密协议 |" in output


def test_render_x_text_uses_longform_cards_and_expands_tables():
    document = parse_markdown(
        """# Title

```text
1. Confirm protocol
2. Confirm certificate
```

```java
System.out.println("ship");
```

| Type | Meaning |
|---|---|
| TLCP | 双证书国密协议 |
"""
    )

    output = render_x_text(document)

    assert "【清单】" in output
    assert "1. Confirm protocol" in output
    assert "[java]" in output
    assert "System.out.println" in output
    assert "【表格】" in output
    assert "Type：TLCP；Meaning：双证书国密协议" in output
