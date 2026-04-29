from video2post.config import AppConfig
from video2post.models import TaskMetadata, TaskStatus, VideoMetadata
from video2post.pipeline import generate_outputs
from video2post.writers.metadata import read_metadata, write_metadata


class FakeProvider:
    model_name = "fake-llm"

    def __init__(self):
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return f"Generated from: {prompt.splitlines()[0]}"


def test_generate_outputs_writes_requested_files_and_updates_metadata(tmp_path):
    metadata = TaskMetadata(
        source_url="https://youtu.be/test",
        platform="youtube",
        task_dir=tmp_path,
        video=VideoMetadata(title="Test Video"),
    )
    write_metadata(metadata)
    (tmp_path / "transcript.en.md").write_text("English transcript", encoding="utf-8")
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    for name in ["translation", "notes", "article", "script", "titles"]:
        (prompt_dir / f"{name}.md").write_text(
            f"{name}: {{{{ video_title }}}}\n{{{{ transcript }}}}",
            encoding="utf-8",
        )
    provider = FakeProvider()

    outputs = generate_outputs(
        tmp_path / "meta.json",
        AppConfig(),
        provider=provider,
        prompt_dir=prompt_dir,
        targets=["translation", "notes", "article", "script", "titles"],
    )

    assert outputs == [
        tmp_path / "transcript.zh.md",
        tmp_path / "notes.md",
        tmp_path / "article.md",
        tmp_path / "script.md",
        tmp_path / "titles.md",
    ]
    assert "Generated from: translation: Test Video" in (
        tmp_path / "transcript.zh.md"
    ).read_text(encoding="utf-8")
    loaded = read_metadata(tmp_path / "meta.json")
    assert loaded.status == TaskStatus.TITLES_GENERATED
    assert loaded.llm_model == "fake-llm"


def test_generate_outputs_uses_default_targets(tmp_path):
    metadata = TaskMetadata(
        source_url="https://youtu.be/test",
        platform="youtube",
        task_dir=tmp_path,
        video=VideoMetadata(title="Test Video"),
    )
    write_metadata(metadata)
    (tmp_path / "transcript.en.md").write_text("English transcript", encoding="utf-8")
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    for name in ["translation", "notes", "article", "script", "titles"]:
        (prompt_dir / f"{name}.md").write_text(name, encoding="utf-8")

    outputs = generate_outputs(
        tmp_path / "meta.json",
        AppConfig(),
        provider=FakeProvider(),
        prompt_dir=prompt_dir,
    )

    assert [path.name for path in outputs] == [
        "transcript.zh.md",
        "notes.md",
        "article.md",
        "script.md",
        "titles.md",
    ]
