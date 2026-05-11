import json

from video2post.config import AppConfig
from video2post.drafts import generate_draft


class SequencedProvider:
    model_name = "fake-draft-llm"

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        if isinstance(self.outputs[0], Exception):
            raise self.outputs.pop(0)
        return self.outputs.pop(0)


def write_prompts(prompt_dir):
    prompt_dir.mkdir()
    for name in [
        "draft_brief",
        "x_engage_replies",
        "x_engage_quote",
        "x_engage_posts",
        "viral_280",
    ]:
        (prompt_dir / f"{name}.md").write_text(
            f"{name}: {{{{ content }}}} {{{{ brief }}}} {{{{ x_url }}}}",
            encoding="utf-8",
        )


def test_generate_x_engage_draft_writes_material_pack(tmp_path):
    prompt_dir = tmp_path / "prompts"
    write_prompts(prompt_dir)
    provider = SequencedProvider([
        "核心提炼",
        "回复1\n回复2\n回复3",
        "引用转发1\n引用转发2",
        "短帖1\n短帖2",
    ])

    result = generate_draft(
        "原始内容：读书笔记里最有价值的一点",
        AppConfig(),
        mode="x_engage",
        x_url="https://x.com/big/status/1",
        output_dir=tmp_path / "drafts",
        provider=provider,
        prompt_dir=prompt_dir,
    )

    assert result.task_dir.parent == tmp_path / "drafts"
    assert [path.name for path in result.paths] == [
        "source.md",
        "brief.md",
        "x_replies.md",
        "x_quote.md",
        "x_posts.md",
    ]
    assert (result.task_dir / "source.md").read_text(encoding="utf-8").startswith("原始内容")
    assert "核心提炼" in (result.task_dir / "brief.md").read_text(encoding="utf-8")
    metadata = json.loads((result.task_dir / "meta.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "completed"
    assert metadata["mode"] == "x_engage"
    assert metadata["x_url"] == "https://x.com/big/status/1"
    assert metadata["llm_model"] == "fake-draft-llm"
    assert "https://x.com/big/status/1" in provider.prompts[1]


def test_generate_viral_280_draft_writes_single_tweet(tmp_path):
    prompt_dir = tmp_path / "prompts"
    write_prompts(prompt_dir)
    tweet = "普通人做内容，别先追爆款。先把一个观点讲清楚。你同意吗？"
    provider = SequencedProvider(["核心提炼", tweet])

    result = generate_draft(
        "原始内容",
        AppConfig(),
        mode="viral_280",
        output_dir=tmp_path / "drafts",
        provider=provider,
        prompt_dir=prompt_dir,
    )

    assert [path.name for path in result.paths] == ["source.md", "brief.md", "viral_280.md"]
    assert (result.task_dir / "viral_280.md").read_text(encoding="utf-8").strip() == tweet
    assert len(tweet) <= 280


def test_generate_viral_280_rejects_overlong_output(tmp_path):
    prompt_dir = tmp_path / "prompts"
    write_prompts(prompt_dir)
    provider = SequencedProvider(["核心提炼", "超" * 281])

    try:
        generate_draft(
            "原始内容",
            AppConfig(),
            mode="viral_280",
            output_dir=tmp_path / "drafts",
            provider=provider,
            prompt_dir=prompt_dir,
        )
    except RuntimeError as error:
        assert "viral_280 output exceeds 280 characters" in str(error)
    else:
        raise AssertionError("Expected overlong viral_280 output to fail")

    task_dir = next((tmp_path / "drafts").iterdir())
    assert not (task_dir / "viral_280.md").exists()
    metadata = json.loads((task_dir / "meta.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "failed"
    assert metadata["error"]["stage"] == "viral_280_validation"


def test_generate_draft_rejects_unknown_mode(tmp_path):
    prompt_dir = tmp_path / "prompts"
    write_prompts(prompt_dir)

    try:
        generate_draft(
            "原始内容",
            AppConfig(),
            mode="unknown",
            output_dir=tmp_path / "drafts",
            provider=SequencedProvider([]),
            prompt_dir=prompt_dir,
        )
    except ValueError as error:
        assert "Unsupported draft mode" in str(error)
    else:
        raise AssertionError("Expected unknown mode to fail")


def test_generate_draft_records_llm_failure(tmp_path):
    prompt_dir = tmp_path / "prompts"
    write_prompts(prompt_dir)
    provider = SequencedProvider([RuntimeError("llm unavailable")])

    try:
        generate_draft(
            "原始内容",
            AppConfig(),
            mode="x_engage",
            output_dir=tmp_path / "drafts",
            provider=provider,
            prompt_dir=prompt_dir,
        )
    except RuntimeError as error:
        assert "llm unavailable" in str(error)
    else:
        raise AssertionError("Expected LLM failure to fail")

    task_dir = next((tmp_path / "drafts").iterdir())
    metadata = json.loads((task_dir / "meta.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "failed"
    assert metadata["error"]["stage"] == "llm_generation"
    assert not (task_dir / "brief.md").exists()


def test_generate_draft_fetches_content_when_only_x_url_is_provided(tmp_path):
    prompt_dir = tmp_path / "prompts"
    write_prompts(prompt_dir)
    provider = SequencedProvider([
        "核心提炼",
        "回复1\n回复2\n回复3",
        "引用转发1\n引用转发2",
        "短帖1\n短帖2",
    ])
    fetched_urls = []

    def fake_fetcher(url):
        fetched_urls.append(url)
        return "来自 X 链接的原推正文"

    result = generate_draft(
        None,
        AppConfig(),
        mode="x_engage",
        x_url="https://x.com/big/status/1",
        output_dir=tmp_path / "drafts",
        provider=provider,
        prompt_dir=prompt_dir,
        x_fetcher=fake_fetcher,
    )

    assert fetched_urls == ["https://x.com/big/status/1"]
    assert (result.task_dir / "source.md").read_text(encoding="utf-8").strip() == "来自 X 链接的原推正文"
    assert "来自 X 链接的原推正文" in provider.prompts[0]
    metadata = json.loads((result.task_dir / "meta.json").read_text(encoding="utf-8"))
    assert metadata["x_url"] == "https://x.com/big/status/1"
    assert metadata["source"] == "x_url"


def test_generate_draft_treats_positional_x_url_as_fetch_source(tmp_path):
    prompt_dir = tmp_path / "prompts"
    write_prompts(prompt_dir)
    provider = SequencedProvider(["核心提炼", "短推内容"])

    result = generate_draft(
        "https://twitter.com/big/status/1",
        AppConfig(),
        mode="viral_280",
        output_dir=tmp_path / "drafts",
        provider=provider,
        prompt_dir=prompt_dir,
        x_fetcher=lambda url: "从 URL 获取的正文",
    )

    assert (result.task_dir / "source.md").read_text(encoding="utf-8").strip() == "从 URL 获取的正文"
    metadata = json.loads((result.task_dir / "meta.json").read_text(encoding="utf-8"))
    assert metadata["x_url"] == "https://twitter.com/big/status/1"
    assert metadata["source"] == "x_url"


def test_generate_draft_records_x_fetch_failure(tmp_path):
    prompt_dir = tmp_path / "prompts"
    write_prompts(prompt_dir)

    def failing_fetcher(url):
        raise RuntimeError("x fetch failed")

    try:
        generate_draft(
            None,
            AppConfig(),
            mode="x_engage",
            x_url="https://x.com/big/status/1",
            output_dir=tmp_path / "drafts",
            provider=SequencedProvider([]),
            prompt_dir=prompt_dir,
            x_fetcher=failing_fetcher,
        )
    except RuntimeError as error:
        assert "x fetch failed" in str(error)
    else:
        raise AssertionError("Expected X fetch failure")

    task_dir = next((tmp_path / "drafts").iterdir())
    metadata = json.loads((task_dir / "meta.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "failed"
    assert metadata["error"]["stage"] == "x_fetch"
    assert not (task_dir / "source.md").exists()
