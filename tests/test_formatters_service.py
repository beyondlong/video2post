from pathlib import Path

from video2post.config import AppConfig
from video2post.formatters.models import FormatRequest, Platform, parse_platforms
from video2post.formatters.service import format_markdown_file, format_task_artifacts


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
    assert "## 引用链接" in (tmp_path / "article.wechat.md").read_text(encoding="utf-8")
    assert (tmp_path / "article.wechat.html").exists()
    assert "OpenAI: https://openai.com" in (tmp_path / "article.x.txt").read_text(encoding="utf-8")


def test_format_markdown_file_uses_output_dir(tmp_path):
    input_path = tmp_path / "article.md"
    output_dir = tmp_path / "publish"
    input_path.write_text("# Title", encoding="utf-8")

    result = format_markdown_file(input_path, platforms=[Platform.X], output_dir=output_dir)

    assert result.paths == [output_dir / "article.x.md", output_dir / "article.x.txt"]


def test_format_task_artifacts_uses_platform_default_sources(tmp_path):
    (tmp_path / "meta.json").write_text("{}", encoding="utf-8")
    (tmp_path / "article.md").write_text("# Article", encoding="utf-8")
    (tmp_path / "x_article.md").write_text("# X Article", encoding="utf-8")

    result = format_task_artifacts(tmp_path, platforms=[Platform.WECHAT, Platform.X])

    assert sorted(path.name for path in result.paths) == [
        "article.wechat.html",
        "article.wechat.md",
        "x_article.x.md",
        "x_article.x.txt",
    ]


def test_format_task_artifacts_falls_back_to_x_article_for_wechat(tmp_path):
    (tmp_path / "meta.json").write_text("{}", encoding="utf-8")
    (tmp_path / "x_article.md").write_text("# X 稿", encoding="utf-8")

    result = format_task_artifacts(tmp_path, platforms=[Platform.WECHAT])

    assert [path.name for path in result.paths] == [
        "x_article.wechat.md",
        "x_article.wechat.html",
    ]


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

    format_markdown_file(input_path, platforms=[Platform.X], rewrite=True)

    assert (tmp_path / "article.x.md").read_text(encoding="utf-8").startswith("# Rewritten")


def test_format_markdown_file_rewrite_can_use_provider_and_config(tmp_path):
    class FakeProvider:
        def __init__(self):
            self.prompts = []

        def generate(self, prompt):
            self.prompts.append(prompt)
            return "# Polished\n\n适合发布的正文"

    input_path = tmp_path / "article.md"
    input_path.write_text("# Original\n\n原始正文", encoding="utf-8")
    provider = FakeProvider()

    format_markdown_file(
        input_path,
        platforms=[Platform.WECHAT, Platform.X],
        rewrite=True,
        config=AppConfig(),
        rewrite_provider=provider,
    )

    assert provider.prompts
    assert "wechat,x" in provider.prompts[0]
    assert "# Original" in provider.prompts[0]
    assert (tmp_path / "article.x.md").read_text(encoding="utf-8").startswith("# Polished")
    assert (tmp_path / "article.wechat.html").exists()


def test_wechat_html_uses_warm_public_account_theme(tmp_path):
    input_path = tmp_path / "article.md"
    input_path.write_text(
        "# 主标题\n\n## 小节\n\n正文包含 `code`。\n\n---\n\n1. 第一项\n2. 第二项\n\n> 说明：重点内容",
        encoding="utf-8",
    )

    format_markdown_file(input_path, platforms=[Platform.WECHAT])

    html = (tmp_path / "article.wechat.html").read_text(encoding="utf-8")
    assert "font-size: 16px; line-height: 1.82; color: #2f2a24;" in html
    assert "font-family: -apple-system, BlinkMacSystemFont" in html
    assert "border-bottom: 1px solid #eadfce" in html
    assert "background: #fbf7ef; border-left: 4px solid #b86b2b" in html
    assert '<hr style="border: 0; border-top: 1px dashed #eadfce; margin: 1.8em 0;" />' in html
    assert '<ol style="margin: 0 0 1.1em 1.2em; padding: 0; color: #6f6254;">' in html
    assert '<code style="background: #f7f1e7;' in html
    assert '<p style="margin: 0 0 0.55em; font-size: 13px; font-weight: 700; color: #8f4f1f;">说明</p>' in html
