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


from video2post.formatters.service import format_task_artifacts


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
