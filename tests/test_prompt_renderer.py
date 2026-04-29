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
