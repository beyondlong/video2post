from video2post.models import TaskStatus
from video2post.writers.markdown import write_markdown
from video2post.writers.workspace import create_task_workspace


def test_create_task_workspace_uses_safe_slug_and_metadata(tmp_path):
    metadata = create_task_workspace(
        output_dir=tmp_path,
        source_url="https://www.youtube.com/watch?v=test",
        platform="youtube",
        title="Python: What is new?",
    )

    assert metadata.task_dir.exists()
    assert metadata.task_dir.name.endswith("python-what-is-new")
    assert (metadata.task_dir / "meta.json").exists()
    assert metadata.status == TaskStatus.CREATED


def test_write_markdown_creates_parent_directories(tmp_path):
    target = tmp_path / "nested" / "article.md"

    write_markdown(target, "# Article\n\nHello")

    assert target.read_text(encoding="utf-8") == "# Article\n\nHello\n"
