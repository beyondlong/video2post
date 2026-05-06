from video2post.formatters.markdown_parser import parse_markdown


def test_parse_markdown_common_blocks():
    document = parse_markdown(
        """# Title

Intro paragraph with **bold**.

> Important quote

- one
- two

1. first
2. second

```python
print("hi")
```

![Alt](image.png)

[Link](https://example.com)

---
"""
    )

    assert [block.kind for block in document.blocks] == [
        "heading",
        "paragraph",
        "blockquote",
        "unordered_list",
        "ordered_list",
        "code_block",
        "paragraph",
        "paragraph",
        "horizontal_rule",
    ]
    assert document.blocks[0].level == 1
    assert document.blocks[5].language == "python"


def test_parse_markdown_tables():
    document = parse_markdown(
        """| 类型 | 本质 | 场景 |
|---|---|---|
| TLCP | 双证书国密协议 | 密评 |
| RFC 8998 | TLS 1.3 国密套件 | 新系统 |
"""
    )

    assert len(document.blocks) == 1
    table = document.blocks[0]
    assert table.kind == "table"
    assert table.headers == ["类型", "本质", "场景"]
    assert table.rows == [
        ["TLCP", "双证书国密协议", "密评"],
        ["RFC 8998", "TLS 1.3 国密套件", "新系统"],
    ]
