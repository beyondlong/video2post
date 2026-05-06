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


def test_resolve_task_source_falls_back_to_article_for_x(tmp_path):
    (tmp_path / "meta.json").write_text("{}", encoding="utf-8")
    (tmp_path / "article.md").write_text("# Article", encoding="utf-8")

    assert resolve_task_source(tmp_path, source=None, platform=Platform.X) == tmp_path / "article.md"
