# 发布格式转换器实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `video2post` 增加一套自包含的 Markdown 发布格式转换能力，先支持任意本地 Markdown 文件，再支持已有 task 产物转换。

**Architecture:** 新增 `video2post/formatters/` 模块承载确定性转换逻辑，CLI 只负责参数解析、路径解析和打印生成文件。默认不调用 LLM；后续通过 `--rewrite` 显式进入可选改写链路。

**Tech Stack:** Python 3.11、Typer、pytest、标准库 `html` / `re` / `dataclasses` / `pathlib`。第一版不新增 Bun、npx 或外部 skill 运行时依赖。

---

## 参考文档

- 总设计：`docs/superpowers/specs/2026-05-06-publish-formatters-design.md`
- CLI 现状：`video2post/cli.py`
- Markdown 写入工具：`video2post/writers/markdown.py`
- CLI 测试风格：`tests/test_cli.py`
- 生成管线测试风格：`tests/test_pipeline_generate.py`

## 文件结构

### 新增文件

- `video2post/formatters/__init__.py`
  - 导出 formatter 对外 API。
- `video2post/formatters/models.py`
  - 定义平台枚举、请求对象、输出对象、转换结果。
- `video2post/formatters/markdown_parser.py`
  - 第一版轻量 Markdown block parser，覆盖常用 Markdown 块级语法。
- `video2post/formatters/links.py`
  - 负责 Markdown 链接和图片识别、外链引用收集、行内文本转换。
- `video2post/formatters/wechat.py`
  - 输出 `*.wechat.md` 和 `*.wechat.html`。
- `video2post/formatters/x_longform.py`
  - 输出 `*.x.md` 和 `*.x.txt`。
- `video2post/formatters/service.py`
  - 编排文件读取、输出路径、平台分发、可选 rewrite 钩子。
- `video2post/formatters/task_sources.py`
  - 解析 task 目录中的 `article`、`x_article`、`notes`、`transcript` 等 source。
- `tests/test_formatters_markdown_parser.py`
- `tests/test_formatters_wechat.py`
- `tests/test_formatters_x_longform.py`
- `tests/test_formatters_service.py`
- `tests/test_formatters_task_sources.py`

### 修改文件

- `video2post/cli.py`
  - 新增 `format` 和 `format-task` 命令。
- `pyproject.toml`
  - 第一版尽量不新增依赖；如实现中决定采用 Markdown parser 依赖，必须在本计划中回写原因并补测试。
- `README.md`
  - 增加发布格式转换命令示例。
- `docs/superpowers/specs/2026-05-06-publish-formatters-design.md`
  - 如果实现阶段确认 open questions，需要同步更新最终决策。

## 关键设计决策

- 第一版使用轻量 block parser，不追求完整 Markdown 规范。
- 行内语法只处理第一版需要的链接、图片、粗体、斜体、代码 span 的基本显示。
- 微信公众号普通外链默认生成文末引用；`mp.weixin.qq.com` 链接保持内联。
- `format-task` 输出文件名包含 source stem，避免不同 source 之间互相覆盖。
- 默认格式化不修改 `meta.json`。
- `--rewrite` 第一轮只打通接口和 opt-in 行为；完整 prompt 质量可后续迭代。

---

## Task 1: Formatter 数据模型和平台解析

**Files:**
- Create: `video2post/formatters/__init__.py`
- Create: `video2post/formatters/models.py`
- Test: `tests/test_formatters_service.py`

- [ ] **Step 1: 写失败测试，覆盖平台解析和输出对象**

在 `tests/test_formatters_service.py` 中添加：

```python
from pathlib import Path

from video2post.formatters.models import FormatRequest, Platform, parse_platforms


def test_parse_platforms_accepts_comma_separated_values():
    assert parse_platforms("wechat,x") == [Platform.WECHAT, Platform.X]


def test_parse_platforms_rejects_unknown_value():
    try:
        parse_platforms("wechat,weibo")
    except ValueError as error:
        assert "Unsupported platform" in str(error)
    else:
        raise AssertionError("Expected unsupported platform error")


def test_format_request_defaults_output_dir_to_input_parent(tmp_path):
    input_path = tmp_path / "article.md"
    input_path.write_text("# Title", encoding="utf-8")

    request = FormatRequest(input_path=input_path, platforms=[Platform.WECHAT])

    assert request.output_dir == tmp_path
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest tests/test_formatters_service.py -q`

Expected: FAIL，提示 `video2post.formatters` 或相关对象不存在。

- [ ] **Step 3: 实现最小模型**

`video2post/formatters/models.py`：

```python
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Platform(StrEnum):
    WECHAT = "wechat"
    X = "x"


def parse_platforms(value: str | None) -> list[Platform]:
    raw_values = [part.strip() for part in (value or "wechat,x").split(",")]
    platforms: list[Platform] = []
    for raw_value in raw_values:
        if not raw_value:
            continue
        try:
            platform = Platform(raw_value)
        except ValueError as error:
            raise ValueError(f"Unsupported platform: {raw_value}") from error
        if platform not in platforms:
            platforms.append(platform)
    return platforms


@dataclass(frozen=True)
class PlatformOutput:
    platform: Platform
    path: Path
    kind: str


@dataclass(frozen=True)
class FormatResult:
    outputs: list[PlatformOutput] = field(default_factory=list)

    @property
    def paths(self) -> list[Path]:
        return [output.path for output in self.outputs]


@dataclass(frozen=True)
class FormatRequest:
    input_path: Path
    platforms: list[Platform]
    output_dir: Path | None = None
    rewrite: bool = False

    def __post_init__(self) -> None:
        if self.output_dir is None:
            object.__setattr__(self, "output_dir", self.input_path.parent)
```

`video2post/formatters/__init__.py`：

```python
"""Markdown publishing formatters."""
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest tests/test_formatters_service.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add video2post/formatters/__init__.py video2post/formatters/models.py tests/test_formatters_service.py
git commit -m "feat: add formatter data models"
```

---

## Task 2: 轻量 Markdown block parser

**Files:**
- Create: `video2post/formatters/markdown_parser.py`
- Modify: `video2post/formatters/models.py`
- Test: `tests/test_formatters_markdown_parser.py`

- [ ] **Step 1: 写失败测试，覆盖第一版常用 Markdown 块**

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest tests/test_formatters_markdown_parser.py -q`

Expected: FAIL，提示 parser 不存在。

- [ ] **Step 3: 实现 block 模型和 parser**

在 `models.py` 增加：

```python
@dataclass(frozen=True)
class MarkdownBlock:
    kind: str
    text: str = ""
    level: int | None = None
    language: str | None = None
    items: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MarkdownDocument:
    blocks: list[MarkdownBlock]
```

`markdown_parser.py` 实现规则：

- 空行分隔段落。
- `#` 到 `######` 识别 heading。
- `>` 连续行合并为 blockquote。
- `- `、`* ` 连续行合并为 unordered list。
- `1. `、`2. ` 连续行合并为 ordered list。
- 三反引号 fenced code block 保留 language 和原始内容。
- `---`、`***`、`___` 识别 horizontal rule。
- 其他连续非空行合并为 paragraph。

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest tests/test_formatters_markdown_parser.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add video2post/formatters/models.py video2post/formatters/markdown_parser.py tests/test_formatters_markdown_parser.py
git commit -m "feat: parse common markdown blocks"
```

---

## Task 3: 行内链接、图片和文本转换工具

**Files:**
- Create: `video2post/formatters/links.py`
- Test: `tests/test_formatters_wechat.py`
- Test: `tests/test_formatters_x_longform.py`

- [ ] **Step 1: 写失败测试，覆盖链接引用和纯文本转换**

在 `tests/test_formatters_wechat.py`：

```python
from video2post.formatters.links import LinkCollector


def test_link_collector_moves_external_links_to_references():
    collector = LinkCollector()

    rendered = collector.render_wechat_markdown(
        "Read [OpenAI](https://openai.com) and [WeChat](https://mp.weixin.qq.com/test)."
    )

    assert "OpenAI[1]" in rendered
    assert "[WeChat](https://mp.weixin.qq.com/test)" in rendered
    assert collector.references == [("OpenAI", "https://openai.com")]
```

在 `tests/test_formatters_x_longform.py`：

```python
from video2post.formatters.links import markdown_inline_to_plain_text


def test_markdown_inline_to_plain_text_expands_links():
    text = markdown_inline_to_plain_text("Read **this** [post](https://example.com).")

    assert text == "Read this post: https://example.com."
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest tests/test_formatters_wechat.py tests/test_formatters_x_longform.py -q`

Expected: FAIL，提示 `links.py` 不存在。

- [ ] **Step 3: 实现链接工具**

`links.py` 提供：

- `LinkCollector.references`
- `render_wechat_markdown(text: str) -> str`
- `render_wechat_html(text: str) -> str`
- `markdown_inline_to_plain_text(text: str) -> str`
- `markdown_inline_to_html(text: str) -> str`

实现约束：

- 普通外链变为 `文本[n]` 并收集引用。
- `https://mp.weixin.qq.com/` 链接保持内联。
- 图片语法 `![alt](src)` 不按普通链接处理。
- 粗体、斜体在纯文本中去除 Markdown 标记。
- HTML 输出必须 `html.escape` 普通文本。

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest tests/test_formatters_wechat.py tests/test_formatters_x_longform.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add video2post/formatters/links.py tests/test_formatters_wechat.py tests/test_formatters_x_longform.py
git commit -m "feat: add formatter inline link utilities"
```

---

## Task 4: 微信公众号 Markdown 输出

**Files:**
- Create: `video2post/formatters/wechat.py`
- Test: `tests/test_formatters_wechat.py`

- [ ] **Step 1: 写失败测试，覆盖 `*.wechat.md` 内容**

```python
from video2post.formatters.markdown_parser import parse_markdown
from video2post.formatters.wechat import render_wechat_markdown


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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest tests/test_formatters_wechat.py -q`

Expected: FAIL，提示 `render_wechat_markdown` 不存在。

- [ ] **Step 3: 实现 WeChat Markdown renderer**

`wechat.py` 提供：

```python
def render_wechat_markdown(document: MarkdownDocument) -> str:
    ...
```

渲染规则：

- heading 保留 `#` 语法。
- paragraph 使用 `LinkCollector.render_wechat_markdown`。
- blockquote 输出 `> text`。
- unordered list 输出 `- item`。
- ordered list 输出 `1. item`。
- code block 保留 fenced code。
- horizontal rule 输出 `---`。
- 文末有 references 时追加：

```markdown
## 引用链接

[1] Title: https://example.com
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest tests/test_formatters_wechat.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add video2post/formatters/wechat.py tests/test_formatters_wechat.py
git commit -m "feat: render wechat markdown"
```

---

## Task 5: 微信公众号 HTML 输出

**Files:**
- Modify: `video2post/formatters/wechat.py`
- Test: `tests/test_formatters_wechat.py`

- [ ] **Step 1: 写失败测试，覆盖内联 CSS 和关键结构**

```python
from video2post.formatters.markdown_parser import parse_markdown
from video2post.formatters.wechat import render_wechat_html


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
    assert "<blockquote" in html
    assert "<pre" in html
    assert "引用链接" in html
    assert "https://openai.com" in html
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest tests/test_formatters_wechat.py -q`

Expected: FAIL，提示 HTML renderer 不存在或断言失败。

- [ ] **Step 3: 实现固定技术文章 HTML 样式**

`wechat.py` 增加：

```python
def render_wechat_html(document: MarkdownDocument) -> str:
    ...
```

样式要求：

- 顶层 `<section>` 使用内联 CSS：`font-size: 16px; line-height: 1.75; color: #1f2933;`。
- `h1` 居中或强标题，间距足够。
- `h2` 使用克制强调，如左边框或底色，但不要花哨。
- `p` 使用合理 margin。
- `blockquote` 使用左边框、浅背景、内边距。
- `pre/code` 使用浅背景、等宽字体、`white-space: pre-wrap; overflow-wrap: break-word;`。
- `img` 使用 `max-width: 100%; height: auto; display: block;`。
- 普通外链在文末引用区展示。

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest tests/test_formatters_wechat.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add video2post/formatters/wechat.py tests/test_formatters_wechat.py
git commit -m "feat: render wechat html"
```

---

## Task 6: X Markdown 和纯文本输出

**Files:**
- Create: `video2post/formatters/x_longform.py`
- Test: `tests/test_formatters_x_longform.py`

- [ ] **Step 1: 写失败测试，覆盖 X 双产物**

```python
from video2post.formatters.markdown_parser import parse_markdown
from video2post.formatters.x_longform import render_x_markdown, render_x_text


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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest tests/test_formatters_x_longform.py -q`

Expected: FAIL，提示 `x_longform.py` 不存在。

- [ ] **Step 3: 实现 X renderer**

`x_longform.py` 提供：

```python
def render_x_markdown(document: MarkdownDocument) -> str:
    ...


def render_x_text(document: MarkdownDocument) -> str:
    ...
```

渲染规则：

- X Markdown 基本保留原 Markdown 结构。
- X 纯文本去掉 Markdown 标记。
- heading 输出为标题文本，前后空行。
- lists 输出为 `- item` 或 `1. item` 的纯文本。
- code block 在纯文本中保留代码内容，但不保留三反引号。
- links 转成 `文本: URL`。

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest tests/test_formatters_x_longform.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add video2post/formatters/x_longform.py tests/test_formatters_x_longform.py
git commit -m "feat: render x longform outputs"
```

---

## Task 7: 文件级格式化 service

**Files:**
- Create: `video2post/formatters/service.py`
- Modify: `video2post/formatters/__init__.py`
- Test: `tests/test_formatters_service.py`

- [ ] **Step 1: 写失败测试，覆盖任意 Markdown 文件输出**

```python
from video2post.formatters.models import Platform
from video2post.formatters.service import format_markdown_file


def test_format_markdown_file_writes_all_selected_outputs(tmp_path):
    input_path = tmp_path / "article.md"
    input_path.write_text("# Title\n\nRead [OpenAI](https://openai.com).", encoding="utf-8")

    result = format_markdown_file(input_path, platforms=[Platform.WECHAT, Platform.X])

    assert sorted(path.name for path in result.paths) == [
        "article.wechat.html",
        "article.wechat.md",
        "article.x.md",
        "article.x.txt",
    ]
    assert (tmp_path / "article.wechat.html").exists()
    assert (tmp_path / "article.x.txt").exists()


def test_format_markdown_file_uses_output_dir(tmp_path):
    input_path = tmp_path / "article.md"
    output_dir = tmp_path / "publish"
    input_path.write_text("# Title", encoding="utf-8")

    result = format_markdown_file(input_path, platforms=[Platform.X], output_dir=output_dir)

    assert result.paths == [output_dir / "article.x.md", output_dir / "article.x.txt"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest tests/test_formatters_service.py -q`

Expected: FAIL，提示 service 不存在。

- [ ] **Step 3: 实现 service**

`service.py` 提供：

```python
def format_markdown_file(
    input_path: Path | str,
    *,
    platforms: list[Platform],
    output_dir: Path | str | None = None,
    rewrite: bool = False,
) -> FormatResult:
    ...
```

要求：

- 输入文件不存在时抛 `FileNotFoundError`。
- 默认不触发 rewrite。
- 创建输出目录。
- 统一写入 UTF-8，确保文件以换行结尾。
- 输出顺序固定：wechat md、wechat html、x md、x txt。

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest tests/test_formatters_service.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add video2post/formatters/service.py video2post/formatters/__init__.py tests/test_formatters_service.py
git commit -m "feat: format markdown files for publishing"
```

---

## Task 8: `video2post format` CLI

**Files:**
- Modify: `video2post/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: 写失败测试，覆盖 CLI 调用 service**

```python
def test_format_command_writes_selected_platform_outputs(tmp_path):
    input_path = tmp_path / "article.md"
    input_path.write_text("# Title", encoding="utf-8")

    result = runner.invoke(
        app,
        ["format", str(input_path), "--platform", "x"],
    )

    assert result.exit_code == 0
    assert "Generated:" in result.output
    assert (tmp_path / "article.x.md").exists()
    assert (tmp_path / "article.x.txt").exists()


def test_format_command_rejects_unknown_platform(tmp_path):
    input_path = tmp_path / "article.md"
    input_path.write_text("# Title", encoding="utf-8")

    result = runner.invoke(app, ["format", str(input_path), "--platform", "weibo"])

    assert result.exit_code != 0
    assert "Unsupported platform" in result.output
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest tests/test_cli.py::test_format_command_writes_selected_platform_outputs tests/test_cli.py::test_format_command_rejects_unknown_platform -q`

Expected: FAIL，提示命令不存在。

- [ ] **Step 3: 实现 CLI 命令**

在 `cli.py` 增加 import：

```python
from video2post.formatters.models import parse_platforms
from video2post.formatters.service import format_markdown_file
```

增加命令：

```python
@app.command("format")
def format_command(
    input_path: Annotated[Path, typer.Argument(help="Markdown file to format.")],
    platform: Annotated[str, typer.Option("--platform", help="Comma-separated platforms: wechat,x.")] = "wechat,x",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output directory.")] = None,
    rewrite: Annotated[bool, typer.Option("--rewrite", help="Rewrite content with the configured LLM before formatting.")] = False,
) -> None:
    platforms = parse_platforms(platform)
    result = format_markdown_file(input_path, platforms=platforms, output_dir=output, rewrite=rewrite)
    _echo_generated_paths(result.paths)
```

错误处理可以先让 Typer 展示异常；如果输出不友好，再补 `try/except ValueError` 并 `raise typer.BadParameter(...)`。

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest tests/test_cli.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add video2post/cli.py tests/test_cli.py
git commit -m "feat: add markdown format command"
```

---

## Task 9: task source 解析和 `format-task` service

**Files:**
- Create: `video2post/formatters/task_sources.py`
- Modify: `video2post/formatters/service.py`
- Test: `tests/test_formatters_task_sources.py`
- Test: `tests/test_formatters_service.py`

- [ ] **Step 1: 写失败测试，覆盖默认 source 选择**

```python
from video2post.formatters.models import Platform
from video2post.formatters.task_sources import resolve_task_source


def test_resolve_task_source_uses_article_for_wechat(tmp_path):
    (tmp_path / "meta.json").write_text("{}", encoding="utf-8")
    (tmp_path / "article.md").write_text("# Article", encoding="utf-8")

    assert resolve_task_source(tmp_path, source=None, platform=Platform.WECHAT) == tmp_path / "article.md"


def test_resolve_task_source_prefers_x_article_for_x(tmp_path):
    (tmp_path / "meta.json").write_text("{}", encoding="utf-8")
    (tmp_path / "article.md").write_text("# Article", encoding="utf-8")
    (tmp_path / "x_article.md").write_text("# X", encoding="utf-8")

    assert resolve_task_source(tmp_path, source=None, platform=Platform.X) == tmp_path / "x_article.md"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest tests/test_formatters_task_sources.py -q`

Expected: FAIL，提示模块不存在。

- [ ] **Step 3: 实现 task source 解析**

`task_sources.py`：

- `article -> article.md`
- `x_article -> x_article.md`
- `notes -> notes.md`
- `transcript -> transcript.en.md` 或 `transcript.zh.md`，优先存在的文件。
- task dir 必须有 `meta.json`，否则抛 `FileNotFoundError`。
- 指定 source 缺失时抛 `FileNotFoundError`，错误中包含 source 名称。

- [ ] **Step 4: 在 service 中增加 task 格式化函数**

```python
def format_task_artifacts(
    task_dir: Path | str,
    *,
    platforms: list[Platform],
    source: str | None = None,
    output_dir: Path | str | None = None,
    rewrite: bool = False,
) -> FormatResult:
    ...
```

注意：当 `platforms=[wechat, x]` 且 `source=None` 时，wechat 和 x 可能选择不同源文件。结果文件名必须保留各自 source stem，例如：

```text
article.wechat.md
article.wechat.html
x_article.x.md
x_article.x.txt
```

- [ ] **Step 5: 运行测试确认通过**

Run: `python3 -m pytest tests/test_formatters_task_sources.py tests/test_formatters_service.py -q`

Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add video2post/formatters/task_sources.py video2post/formatters/service.py tests/test_formatters_task_sources.py tests/test_formatters_service.py
git commit -m "feat: resolve task artifacts for publishing formats"
```

---

## Task 10: `video2post format-task` CLI

**Files:**
- Modify: `video2post/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: 写失败测试，覆盖 task 命令**

```python
def test_format_task_command_uses_existing_artifacts(tmp_path):
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    (task_dir / "meta.json").write_text("{}", encoding="utf-8")
    (task_dir / "article.md").write_text("# Article", encoding="utf-8")

    result = runner.invoke(app, ["format-task", str(task_dir), "--platform", "wechat"])

    assert result.exit_code == 0
    assert (task_dir / "article.wechat.md").exists()
    assert (task_dir / "article.wechat.html").exists()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest tests/test_cli.py::test_format_task_command_uses_existing_artifacts -q`

Expected: FAIL，提示命令不存在。

- [ ] **Step 3: 实现 CLI 命令**

在 `cli.py` 引入：

```python
from video2post.formatters.service import format_markdown_file, format_task_artifacts
```

新增：

```python
@app.command("format-task")
def format_task_command(
    task_dir: Annotated[Path, typer.Argument(help="Existing video2post task directory.")],
    source: Annotated[str | None, typer.Option("--source", help="Task artifact source: article,x_article,notes,transcript.")] = None,
    platform: Annotated[str, typer.Option("--platform", help="Comma-separated platforms: wechat,x.")] = "wechat,x",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output directory.")] = None,
    rewrite: Annotated[bool, typer.Option("--rewrite", help="Rewrite content with the configured LLM before formatting.")] = False,
) -> None:
    platforms = parse_platforms(platform)
    result = format_task_artifacts(task_dir, platforms=platforms, source=source, output_dir=output, rewrite=rewrite)
    _echo_generated_paths(result.paths)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest tests/test_cli.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add video2post/cli.py tests/test_cli.py
git commit -m "feat: add task formatting command"
```

---

## Task 11: `--rewrite` opt-in 骨架

**Files:**
- Create: `video2post/formatters/rewrite.py`
- Modify: `video2post/formatters/service.py`
- Test: `tests/test_formatters_service.py`

- [ ] **Step 1: 写失败测试，确认默认不 rewrite、显式才 rewrite**

```python
from video2post.formatters.models import Platform
from video2post.formatters.service import format_markdown_file


def test_format_markdown_file_does_not_rewrite_by_default(tmp_path, monkeypatch):
    input_path = tmp_path / "article.md"
    input_path.write_text("# Original", encoding="utf-8")

    def fail_rewrite(*args, **kwargs):
        raise AssertionError("rewrite should not run")

    monkeypatch.setattr("video2post.formatters.service.rewrite_markdown", fail_rewrite)

    format_markdown_file(input_path, platforms=[Platform.X])


def test_format_markdown_file_rewrites_when_requested(tmp_path, monkeypatch):
    input_path = tmp_path / "article.md"
    input_path.write_text("# Original", encoding="utf-8")

    monkeypatch.setattr(
        "video2post.formatters.service.rewrite_markdown",
        lambda content, platforms: "# Rewritten",
    )

    result = format_markdown_file(input_path, platforms=[Platform.X], rewrite=True)

    assert (tmp_path / "article.x.md").read_text(encoding="utf-8").startswith("# Rewritten")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest tests/test_formatters_service.py -q`

Expected: FAIL，提示 rewrite 函数不存在或未接入。

- [ ] **Step 3: 实现 rewrite 骨架**

`rewrite.py`：

```python
from video2post.formatters.models import Platform


def rewrite_markdown(content: str, platforms: list[Platform]) -> str:
    raise RuntimeError("Markdown rewrite is not implemented yet. Run without --rewrite for deterministic formatting.")
```

`service.py` 中仅在 `rewrite=True` 时调用。

如果要第一版完整接 LLM，可在此任务后追加独立任务，不要混入确定性转换任务。

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest tests/test_formatters_service.py -q`

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add video2post/formatters/rewrite.py video2post/formatters/service.py tests/test_formatters_service.py
git commit -m "feat: add opt-in formatter rewrite hook"
```

---

## Task 12: 文档和端到端验收

**Files:**
- Modify: `README.md`
- Create: `docs/publish-formatters.md`
- Test: no new unit test unless docs examples reveal gaps

- [ ] **Step 1: 增加 README 简短说明**

在 README 的命令示例区域增加：

```bash
video2post format article.md --platform wechat,x
video2post format article.md --platform wechat --output ./publish-ready
video2post format-task ./outputs/2026-... --source article --platform wechat,x
```

说明生成文件：

```text
*.wechat.md
*.wechat.html
*.x.md
*.x.txt
```

- [ ] **Step 2: 新增详细文档 `docs/publish-formatters.md`**

内容包括：

- 任意 Markdown 文件转换。
- task 产物转换。
- 默认不调用 LLM。
- `--rewrite` 当前状态。
- 微信 HTML 风格参考 baoyu skill，但不依赖 Bun/npx。
- 第一版支持和不支持的 Markdown 语法。

- [ ] **Step 3: 手动端到端验收**

创建临时 fixture：

```bash
mkdir -p /tmp/video2post-format-check
cat > /tmp/video2post-format-check/article.md <<'MD'
# Demo

这是一段 **加粗** 内容，包含 [OpenAI](https://openai.com)。

> 关键观点

```python
print("hello")
```

![cover](cover.png)

---
MD
python3 -m video2post.cli format /tmp/video2post-format-check/article.md --platform wechat,x
```

Expected files:

```text
/tmp/video2post-format-check/article.wechat.md
/tmp/video2post-format-check/article.wechat.html
/tmp/video2post-format-check/article.x.md
/tmp/video2post-format-check/article.x.txt
```

检查点：

- `article.wechat.html` 包含 `<section style=`。
- `article.wechat.md` 包含 `## 引用链接`。
- `article.x.txt` 不包含 `**`。
- 命令输出打印所有 `Generated:` 路径。

- [ ] **Step 4: 跑相关测试**

Run:

```bash
python3 -m pytest tests/test_formatters_markdown_parser.py tests/test_formatters_wechat.py tests/test_formatters_x_longform.py tests/test_formatters_service.py tests/test_formatters_task_sources.py tests/test_cli.py -q
```

Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add README.md docs/publish-formatters.md
git commit -m "docs: document publishing formatters"
```

---

## 最终验收清单

- [ ] `video2post format article.md --platform wechat,x` 生成四个文件。
- [ ] `video2post format article.md --platform wechat --output DIR` 输出到指定目录。
- [ ] `video2post format-task TASK_DIR --platform wechat,x` 能按默认 source 生成文件。
- [ ] 微信 HTML 使用内联 CSS，能体现清爽技术文章风格。
- [ ] 微信 Markdown 能把普通外链转成文末引用。
- [ ] X Markdown 保留结构。
- [ ] X 纯文本适合直接粘贴，不残留明显 Markdown 噪音。
- [ ] 默认路径不调用 LLM。
- [ ] `--rewrite` 是显式 opt-in。
- [ ] 相关 pytest 全部通过。
