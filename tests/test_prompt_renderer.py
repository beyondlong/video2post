from video2post.llm.prompts import PromptRenderer


def test_prompt_renderer_replaces_template_variables(tmp_path):
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    (prompt_dir / "article.md").write_text(
        "Title: {{ video_title }}\nTranscript: {{ transcript }}",
        encoding="utf-8",
    )

    renderer = PromptRenderer(prompt_dir)
    rendered = renderer.render(
        "article",
        {
            "video_title": "Codex Demo",
            "transcript": "Hello",
        },
    )

    assert rendered == "Title: Codex Demo\nTranscript: Hello"


def test_prompt_renderer_leaves_unknown_variables_empty(tmp_path):
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    (prompt_dir / "notes.md").write_text("{{ missing }}", encoding="utf-8")

    renderer = PromptRenderer(prompt_dir)

    assert renderer.render("notes", {}) == ""


def test_prompt_renderer_falls_back_to_repo_prompts_from_other_working_directory(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    renderer = PromptRenderer("prompts")

    rendered = renderer.render(
        "chunk_summary",
        {
            "video_title": "Codex Demo",
            "platform": "youtube",
            "source_url": "https://youtu.be/test",
            "chunk_index": 1,
            "chunk_count": 2,
            "transcript_chunk": "hello world",
        },
    )

    assert "hello world" in rendered
