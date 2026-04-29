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


class FailingProvider:
    model_name = "failing-llm"

    def generate(self, prompt):
        raise RuntimeError("llm unavailable")


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


def test_generate_outputs_summarizes_large_transcript_in_chunks(tmp_path):
    metadata = TaskMetadata(
        source_url="https://youtu.be/test",
        platform="youtube",
        task_dir=tmp_path,
        video=VideoMetadata(title="Long Video"),
    )
    write_metadata(metadata)
    (tmp_path / "transcript.en.md").write_text(
        "paragraph one has enough text\n\nparagraph two has enough text\n\nparagraph three",
        encoding="utf-8",
    )
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    (prompt_dir / "chunk_summary.md").write_text(
        "summarize chunk {{ chunk_index }} of {{ chunk_count }}\n{{ transcript_chunk }}",
        encoding="utf-8",
    )
    (prompt_dir / "notes.md").write_text(
        "final notes for {{ video_title }}\n{{ transcript }}",
        encoding="utf-8",
    )
    provider = FakeProvider()

    outputs = generate_outputs(
        tmp_path / "meta.json",
        AppConfig.model_validate({"generation": {"chunk_max_chars": 35}}),
        provider=provider,
        prompt_dir=prompt_dir,
        targets=["notes"],
    )

    assert outputs == [tmp_path / "notes.md"]
    assert [path.name for path in sorted((tmp_path / "chunks").glob("*.md"))] == [
        "chunk-001.md",
        "chunk-002.md",
        "chunk-003.md",
    ]
    assert [path.name for path in sorted((tmp_path / "summaries").glob("*.md"))] == [
        "chunk-001.summary.md",
        "chunk-002.summary.md",
        "chunk-003.summary.md",
    ]
    assert len(provider.prompts) == 4
    assert provider.prompts[0].startswith("summarize chunk 1 of 3")
    assert "Generated from: summarize chunk 1 of 3" in provider.prompts[-1]
    assert "paragraph one has enough text" in (
        tmp_path / "chunks" / "chunk-001.md"
    ).read_text(encoding="utf-8")


def test_generate_outputs_records_failure_when_chunk_summary_fails(tmp_path):
    metadata = TaskMetadata(
        source_url="https://youtu.be/test",
        platform="youtube",
        task_dir=tmp_path,
        video=VideoMetadata(title="Long Video"),
    )
    write_metadata(metadata)
    (tmp_path / "transcript.en.md").write_text("one\n\ntwo\n\nthree", encoding="utf-8")
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    (prompt_dir / "chunk_summary.md").write_text(
        "{{ transcript_chunk }}",
        encoding="utf-8",
    )

    try:
        generate_outputs(
            tmp_path / "meta.json",
            AppConfig.model_validate({"generation": {"chunk_max_chars": 5}}),
            provider=FailingProvider(),
            prompt_dir=prompt_dir,
            targets=["notes"],
        )
    except RuntimeError:
        pass

    loaded = read_metadata(tmp_path / "meta.json")
    assert loaded.status == TaskStatus.FAILED
    assert loaded.error.stage == "llm_generation"
    assert loaded.error.retryable is True
