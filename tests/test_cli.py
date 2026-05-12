from pathlib import Path
import subprocess

from typer.testing import CliRunner

from video2post.cli import app
from video2post.models import TaskMetadata, TaskStatus, VideoMetadata
from video2post.writers.metadata import write_metadata


runner = CliRunner()


def test_cli_help_shows_application_name():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "video2post" in result.output



def test_video_help_documents_fast_and_targets():
    result = runner.invoke(app, ["video", "--help"])

    assert result.exit_code == 0
    compact_output = "".join(result.output.split())
    assert "notes,x_article,x_thread,x_titles,publish_formats" in compact_output
    assert "translation,notes,x_article,x_thread,x_titles,article,script,titles,cover,publish_formats" in compact_output


def test_format_help_documents_source_fallback():
    result = runner.invoke(app, ["format", "--help"])

    assert result.exit_code == 0
    compact_output = " ".join(result.output.split())
    assert "Task artifact source" in compact_output

def test_cli_exposes_simplified_top_level_commands():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "video" in result.output
    assert "draft" in result.output
    assert "format" in result.output
    assert "task" in result.output
    assert "process" not in result.output
    assert "format-task" not in result.output


def test_old_workflow_commands_are_removed():
    for command in ["process", "generate", "retry", "tasks", "format-task"]:
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code != 0


def test_task_help_exposes_task_subcommands():
    result = runner.invoke(app, ["task", "--help"])

    assert result.exit_code == 0
    assert "generate" in result.output
    assert "retry" in result.output
    assert "list" in result.output


def test_config_show_prints_effective_config():
    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "output_dir" in result.output
    assert "openai_compatible" in result.output




def test_draft_command_generates_x_engage_pack(monkeypatch, tmp_path):
    class FakeDraftResult:
        def __init__(self):
            self.task_dir = tmp_path / "drafts" / "2026-05-11-test"
            self.paths = [self.task_dir / "source.md", self.task_dir / "x_replies.md"]

    calls = []

    def fake_generate_draft(
        content, config, *, mode, x_url=None, output_dir=None, title=None, progress_callback=None, x_fetch_mode="auto"
    ):
        calls.append((content, mode, x_url, output_dir, title, x_fetch_mode))
        if progress_callback:
            progress_callback("Generating draft brief...")
        return FakeDraftResult()

    monkeypatch.setattr("video2post.cli.generate_draft", fake_generate_draft)

    result = runner.invoke(
        app,
        [
            "draft",
            "一段收藏内容",
            "--mode",
            "x_engage",
            "--x-url",
            "https://x.com/big/status/1",
            "--output",
            str(tmp_path / "drafts"),
        ],
    )

    assert result.exit_code == 0
    assert calls == [("一段收藏内容", "x_engage", "https://x.com/big/status/1", tmp_path / "drafts", None, "auto")]
    assert "Draft directory:" in result.output
    assert "Progress: Generating draft brief..." in result.output
    assert "Generated:" in result.output




def test_draft_command_accepts_x_url_without_content(monkeypatch):
    class FakeDraftResult:
        def __init__(self):
            self.task_dir = Path("drafts/2026-05-11-test")
            self.paths = [self.task_dir / "source.md"]

    calls = []

    def fake_generate_draft(
        content, config, *, mode, x_url=None, output_dir=None, title=None, progress_callback=None, x_fetch_mode="auto"
    ):
        calls.append((content, mode, x_url, x_fetch_mode))
        return FakeDraftResult()

    monkeypatch.setattr("video2post.cli.generate_draft", fake_generate_draft)

    result = runner.invoke(app, ["draft", "--x-url", "https://x.com/big/status/1"])

    assert result.exit_code == 0
    assert calls == [(None, "x_engage", "https://x.com/big/status/1", "auto")]


def test_draft_command_accepts_x_url_as_content(monkeypatch):
    class FakeDraftResult:
        def __init__(self):
            self.task_dir = Path("drafts/2026-05-11-test")
            self.paths = [self.task_dir / "source.md"]

    calls = []

    def fake_generate_draft(
        content, config, *, mode, x_url=None, output_dir=None, title=None, progress_callback=None, x_fetch_mode="auto"
    ):
        calls.append((content, mode, x_url, x_fetch_mode))
        return FakeDraftResult()

    monkeypatch.setattr("video2post.cli.generate_draft", fake_generate_draft)

    result = runner.invoke(app, ["draft", "https://x.com/big/status/1", "--mode", "viral_280"])

    assert result.exit_code == 0
    assert calls == [("https://x.com/big/status/1", "viral_280", None, "auto")]


def test_draft_command_reports_generation_failure(monkeypatch):
    def fake_generate_draft(*args, **kwargs):
        raise RuntimeError("viral_280 output exceeds 280 characters")

    monkeypatch.setattr("video2post.cli.generate_draft", fake_generate_draft)

    result = runner.invoke(app, ["draft", "一段收藏内容", "--mode", "viral_280"])

    assert result.exit_code == 1
    assert "viral_280 output exceeds 280 characters" in result.output


def test_samples_command_lists_builtin_regression_cases():
    result = runner.invoke(app, ["samples"])

    assert result.exit_code == 0
    assert "youtube-short-tech" in result.output
    assert "bilibili-short-cn" in result.output
    assert "invalid-url" in result.output


def test_doctor_command_reports_results(monkeypatch):
    from video2post.doctor import DoctorCheck, DoctorStatus

    monkeypatch.setattr(
        "video2post.cli.collect_doctor_checks",
        lambda: [
            DoctorCheck(name="ffmpeg", status=DoctorStatus.OK, detail="/opt/homebrew/bin/ffmpeg"),
            DoctorCheck(
                name="python:mlx_whisper",
                status=DoctorStatus.OK,
                detail="mlx-whisper importable",
                required=False,
            ),
            DoctorCheck(
                name="python:funasr",
                status=DoctorStatus.OPTIONAL,
                detail="funasr not installed",
                required=False,
            ),
        ],
    )

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "[OK] ffmpeg" in result.output
    assert "[OK] python:mlx_whisper" in result.output
    assert "[OPTIONAL] python:funasr" in result.output
    assert "Doctor summary: required dependencies look ready." in result.output


def test_doctor_command_returns_non_zero_when_required_items_are_missing(monkeypatch):
    from video2post.doctor import DoctorCheck, DoctorStatus

    monkeypatch.setattr(
        "video2post.cli.collect_doctor_checks",
        lambda: [
            DoctorCheck(name="ffmpeg", status=DoctorStatus.MISSING, detail="command not found"),
        ],
    )

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "[MISSING] ffmpeg" in result.output


def test_video_uses_configured_output_directory(tmp_path):
    config_file = tmp_path / "config.yaml"
    configured_output = tmp_path / "configured-output"
    config_file.write_text(
        f"""
app:
  output_dir: {configured_output}
""".strip(),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "video",
            "https://www.youtube.com/watch?v=abc",
            "--config",
            str(config_file),
            "--no-download",
        ],
    )

    assert result.exit_code == 0
    assert str(configured_output) in result.output
    assert list(configured_output.glob("*/meta.json"))


def test_video_output_option_overrides_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    configured_output = tmp_path / "configured-output"
    overridden_output = tmp_path / "overridden-output"
    config_file.write_text(
        f"""
app:
  output_dir: {configured_output}
""".strip(),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "video",
            "https://www.youtube.com/watch?v=abc",
            "--config",
            str(config_file),
            "--output",
            str(overridden_output),
            "--no-download",
        ],
    )

    assert result.exit_code == 0
    assert str(overridden_output) in result.output
    assert not configured_output.exists()
    assert list(overridden_output.glob("*/meta.json"))


def test_video_cleanup_source_option_overrides_config(tmp_path):
    result = runner.invoke(
        app,
        [
            "video",
            "https://www.youtube.com/watch?v=abc",
            "--output",
            str(tmp_path),
            "--cleanup-source",
            "--no-download",
        ],
    )

    assert result.exit_code == 0
    assert "Source cleanup: enabled" in result.output


def test_video_marks_metadata_fetched_when_initial_metadata_exists(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "video2post.cli.fetch_initial_video_metadata",
        lambda url, config=None: VideoMetadata(title="Fetched Title", author="Author"),
    )

    result = runner.invoke(
        app,
        [
            "video",
            "https://www.youtube.com/watch?v=abc",
            "--output",
            str(tmp_path),
            "--no-download",
        ],
    )

    metadata = TaskMetadata.model_validate_json(
        list(tmp_path.glob("*/meta.json"))[0].read_text(encoding="utf-8")
    )
    assert result.exit_code == 0
    assert metadata.status == TaskStatus.METADATA_FETCHED
    assert metadata.video.author == "Author"


def test_video_can_run_full_pipeline_with_generate(monkeypatch, tmp_path):
    calls = []

    def fake_fetch_metadata(url, config=None):
        calls.append(("fetch_metadata", url, config.download.cookies_from_browser))
        from video2post.models import VideoMetadata

        return VideoMetadata(title="Real Video Title")

    def fake_prepare(metadata_path, config):
        calls.append(("audio", metadata_path.name))
        return metadata_path.parent / "audio.wav"

    def fake_transcribe(metadata_path, config):
        calls.append(("transcribe", metadata_path.name))
        return metadata_path.parent / "transcript.en.md"

    def fake_generate(metadata_path, config, targets=None, cover_at=None, progress_callback=None):
        calls.append(("generate", tuple(targets or [])))
        return [metadata_path.parent / "titles.md"]

    monkeypatch.setattr("video2post.cli.fetch_initial_video_metadata", fake_fetch_metadata)
    monkeypatch.setattr("video2post.cli.prepare_audio", fake_prepare)
    monkeypatch.setattr("video2post.cli.transcribe_audio", fake_transcribe)
    monkeypatch.setattr("video2post.cli.generate_outputs", fake_generate)

    result = runner.invoke(
        app,
        [
            "video",
            "https://www.youtube.com/watch?v=abc",
            "--output",
            str(tmp_path),
            "--generate",
            "--targets",
            "titles",
        ],
    )

    assert result.exit_code == 0
    assert calls == [
        ("fetch_metadata", "https://www.youtube.com/watch?v=abc", "chrome"),
        ("audio", "meta.json"),
        ("transcribe", "meta.json"),
        ("generate", ("titles",)),
    ]
    assert list(tmp_path.glob("*/meta.json"))[0].parent.name.endswith("real-video-title")
    assert "Transcript:" in result.output
    assert "Generated:" in result.output


def test_video_fast_generates_default_quick_targets_without_generate_flag(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(
        "video2post.cli.fetch_initial_video_metadata",
        lambda url, config=None: VideoMetadata(title="Fast Video"),
    )
    monkeypatch.setattr(
        "video2post.cli.prepare_audio",
        lambda metadata_path, config: metadata_path.parent / "audio.wav",
    )
    monkeypatch.setattr(
        "video2post.cli.transcribe_audio",
        lambda metadata_path, config: metadata_path.parent / "transcript.en.md",
    )

    def fake_generate(metadata_path, config, targets=None, cover_at=None, progress_callback=None):
        calls.append(tuple(targets or []))
        return [metadata_path.parent / "x_article.md"]

    monkeypatch.setattr("video2post.cli.generate_outputs", fake_generate)

    result = runner.invoke(
        app,
        [
            "video",
            "https://www.youtube.com/watch?v=abc",
            "--output",
            str(tmp_path),
            "--fast",
        ],
    )

    assert result.exit_code == 0
    assert calls == [("notes", "x_article", "x_thread", "x_titles", "publish_formats")]


def test_video_fast_respects_explicit_targets(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(
        "video2post.cli.fetch_initial_video_metadata",
        lambda url, config=None: VideoMetadata(title="Fast Video"),
    )
    monkeypatch.setattr(
        "video2post.cli.prepare_audio",
        lambda metadata_path, config: metadata_path.parent / "audio.wav",
    )
    monkeypatch.setattr(
        "video2post.cli.transcribe_audio",
        lambda metadata_path, config: metadata_path.parent / "transcript.en.md",
    )

    def fake_generate(metadata_path, config, targets=None, cover_at=None, progress_callback=None):
        calls.append(tuple(targets or []))
        return [metadata_path.parent / "notes.md"]

    monkeypatch.setattr("video2post.cli.generate_outputs", fake_generate)

    result = runner.invoke(
        app,
        [
            "video",
            "https://www.youtube.com/watch?v=abc",
            "--output",
            str(tmp_path),
            "--fast",
            "--targets",
            "notes",
        ],
    )

    assert result.exit_code == 0
    assert calls == [("notes",)]


def test_video_can_skip_transcribe_and_generate(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(
        "video2post.cli.fetch_initial_video_metadata",
        lambda url, config=None: calls.append(("fetch_metadata", config)) or None,
    )
    monkeypatch.setattr(
        "video2post.cli.prepare_audio",
        lambda metadata_path, config: calls.append("audio") or metadata_path.parent / "audio.wav",
    )
    monkeypatch.setattr(
        "video2post.cli.transcribe_audio",
        lambda metadata_path, config: calls.append("transcribe"),
    )
    monkeypatch.setattr(
        "video2post.cli.generate_outputs",
        lambda metadata_path, config, targets=None: calls.append("generate"),
    )

    result = runner.invoke(
        app,
        [
            "video",
            "https://www.youtube.com/watch?v=abc",
            "--output",
            str(tmp_path),
            "--no-transcribe",
            "--no-generate",
        ],
    )

    assert result.exit_code == 0
    assert len(calls) == 2
    assert calls[0][0] == "fetch_metadata"
    assert calls[0][1] is not None
    assert calls[1] == "audio"


def test_video_uses_loaded_config_for_initial_metadata_fetch(monkeypatch, tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
download:
  cookies_from_browser: chrome
  js_runtimes: node
  remote_components: ejs:github
""".strip(),
        encoding="utf-8",
    )
    calls = []

    def fake_fetch_metadata(url, config=None):
        calls.append(
            (
                url,
                config.download.cookies_from_browser,
                config.download.js_runtimes,
                config.download.remote_components,
            )
        )
        return VideoMetadata(title="Configured Title")

    monkeypatch.setattr("video2post.cli.fetch_initial_video_metadata", fake_fetch_metadata)
    monkeypatch.setattr(
        "video2post.cli.prepare_audio",
        lambda metadata_path, config: metadata_path.parent / "audio.wav",
    )

    result = runner.invoke(
        app,
        [
            "video",
            "https://www.youtube.com/watch?v=abc",
            "--config",
            str(config_file),
            "--output",
            str(tmp_path / "outputs"),
            "--no-transcribe",
            "--no-generate",
        ],
    )

    assert result.exit_code == 0
    assert calls == [
        (
            "https://www.youtube.com/watch?v=abc",
            "chrome",
            "node",
            "ejs:github",
        )
    ]
    assert list((tmp_path / "outputs").glob("*/meta.json"))[0].parent.name.endswith(
        "configured-title"
    )


def test_task_generate_command_prints_progress_messages(monkeypatch, tmp_path):
    _write_task_metadata(tmp_path, status=TaskStatus.TRANSCRIBED)

    def fake_generate(metadata_path_arg, config, targets=None, cover_at=None, progress_callback=None):
        progress_callback("Generating notes...")
        progress_callback("Generated notes.md")
        return [metadata_path_arg.parent / "notes.md"]

    monkeypatch.setattr("video2post.cli.generate_outputs", fake_generate)

    result = runner.invoke(app, ["task", "generate", str(tmp_path), "--targets", "notes"])

    assert result.exit_code == 0
    assert "Progress: Generating notes..." in result.output
    assert "Progress: Generated notes.md" in result.output
    assert "Generated:" in result.output


def test_task_generate_command_regenerates_selected_targets(monkeypatch, tmp_path):
    metadata_path = _write_task_metadata(tmp_path, status=TaskStatus.TRANSCRIBED)
    calls = []

    def fake_generate(metadata_path_arg, config, targets=None, cover_at=None, progress_callback=None):
        calls.append((metadata_path_arg, tuple(targets or [])))
        return [metadata_path_arg.parent / "titles.md"]

    monkeypatch.setattr("video2post.cli.generate_outputs", fake_generate)

    result = runner.invoke(
        app,
        [
            "task",
            "generate",
            str(tmp_path),
            "--targets",
            "titles",
        ],
    )

    assert result.exit_code == 0
    assert calls == [(metadata_path, ("titles",))]
    assert "Generated:" in result.output


def test_task_generate_command_passes_cover_time(monkeypatch, tmp_path):
    metadata_path = _write_task_metadata(tmp_path, status=TaskStatus.TRANSCRIBED)
    calls = []

    def fake_generate(metadata_path_arg, config, targets=None, cover_at=None, progress_callback=None):
        calls.append((metadata_path_arg, tuple(targets or []), cover_at))
        return [metadata_path_arg.parent / "cover.jpg"]

    monkeypatch.setattr("video2post.cli.generate_outputs", fake_generate)

    result = runner.invoke(
        app,
        [
            "task",
            "generate",
            str(tmp_path),
            "--targets",
            "cover",
            "--cover-at",
            "00:00:30",
        ],
    )

    assert result.exit_code == 0
    assert calls == [(metadata_path, ("cover",), "00:00:30")]


def test_task_retry_transcribes_when_audio_exists_but_transcript_is_missing(monkeypatch, tmp_path):
    metadata_path = _write_task_metadata(tmp_path, status=TaskStatus.AUDIO_NORMALIZED)
    (tmp_path / "audio.wav").write_bytes(b"audio")
    calls = []

    monkeypatch.setattr(
        "video2post.cli.prepare_audio",
        lambda metadata_path_arg, config: calls.append("audio")
        or metadata_path_arg.parent / "audio.wav",
    )
    monkeypatch.setattr(
        "video2post.cli.transcribe_audio",
        lambda metadata_path_arg, config: calls.append(("transcribe", metadata_path_arg))
        or metadata_path_arg.parent / "transcript.en.md",
    )
    monkeypatch.setattr(
        "video2post.cli.generate_outputs",
        lambda metadata_path_arg, config, targets=None: calls.append("generate"),
    )

    result = runner.invoke(app, ["task", "retry", str(tmp_path)])

    assert result.exit_code == 0
    assert calls == [("transcribe", metadata_path)]
    assert "Transcript:" in result.output


def test_task_retry_can_generate_after_transcription(monkeypatch, tmp_path):
    metadata_path = _write_task_metadata(tmp_path, status=TaskStatus.TRANSCRIBED)
    (tmp_path / "audio.wav").write_bytes(b"audio")
    (tmp_path / "transcript.en.md").write_text("transcript", encoding="utf-8")
    calls = []

    monkeypatch.setattr(
        "video2post.cli.prepare_audio",
        lambda metadata_path_arg, config: calls.append("audio"),
    )
    monkeypatch.setattr(
        "video2post.cli.transcribe_audio",
        lambda metadata_path_arg, config: calls.append("transcribe"),
    )
    monkeypatch.setattr(
        "video2post.cli.generate_outputs",
        lambda metadata_path_arg, config, targets=None, cover_at=None, progress_callback=None: calls.append(
            ("generate", tuple(targets or []))
        )
        or [metadata_path_arg.parent / "titles.md"],
    )

    result = runner.invoke(
        app,
        [
            "task",
            "retry",
            str(tmp_path),
            "--generate",
            "--targets",
            "titles",
        ],
    )

    assert result.exit_code == 0
    assert calls == [("generate", ("titles",))]
    assert "Generated:" in result.output


def test_task_retry_bilibili_uses_chinese_transcript_as_completion_signal(monkeypatch, tmp_path):
    metadata_path = _write_task_metadata(
        tmp_path,
        status=TaskStatus.TRANSCRIBED,
        platform="bilibili",
        source_url="https://www.bilibili.com/video/BV123",
    )
    (tmp_path / "audio.wav").write_bytes(b"audio")
    (tmp_path / "transcript.zh.md").write_text("中文整理稿", encoding="utf-8")
    calls = []

    monkeypatch.setattr(
        "video2post.cli.prepare_audio",
        lambda metadata_path_arg, config: calls.append("audio"),
    )
    monkeypatch.setattr(
        "video2post.cli.transcribe_audio",
        lambda metadata_path_arg, config: calls.append("transcribe"),
    )

    result = runner.invoke(app, ["task", "retry", str(tmp_path)])

    assert result.exit_code == 0
    assert calls == []
    assert "Nothing to retry." in result.output


def test_video_generate_uses_configured_chunk_size(monkeypatch, tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
generation:
  chunk_max_chars: 42
""".strip(),
        encoding="utf-8",
    )
    calls = []

    monkeypatch.setattr(
        "video2post.cli.fetch_initial_video_metadata",
        lambda url, config=None: None,
    )
    monkeypatch.setattr(
        "video2post.cli.prepare_audio",
        lambda metadata_path, config: metadata_path.parent / "audio.wav",
    )
    monkeypatch.setattr(
        "video2post.cli.transcribe_audio",
        lambda metadata_path, config: metadata_path.parent / "transcript.en.md",
    )

    def fake_generate(metadata_path, config, targets=None, cover_at=None, progress_callback=None):
        calls.append((config.generation.chunk_max_chars, tuple(targets or [])))
        return [metadata_path.parent / "notes.md"]

    monkeypatch.setattr("video2post.cli.generate_outputs", fake_generate)

    result = runner.invoke(
        app,
        [
            "video",
            "https://www.youtube.com/watch?v=abc",
            "--config",
            str(config_file),
            "--output",
            str(tmp_path / "outputs"),
            "--generate",
            "--targets",
            "notes",
        ],
    )

    assert result.exit_code == 0
    assert calls == [(42, ("notes",))]


def test_video_youtube_can_force_chinese_language(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(
        "video2post.cli.fetch_initial_video_metadata",
        lambda url, config=None: VideoMetadata(title="Chinese YouTube"),
    )
    monkeypatch.setattr(
        "video2post.cli.prepare_audio",
        lambda metadata_path, config: metadata_path.parent / "audio.wav",
    )

    def fake_transcribe(metadata_path, config):
        metadata = TaskMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
        calls.append(("transcribe", metadata.source_language))
        transcript = metadata_path.parent / "transcript.zh.md"
        transcript.write_text("中文转写稿", encoding="utf-8")
        return transcript

    def fake_generate(metadata_path, config, targets=None, cover_at=None, progress_callback=None):
        metadata = TaskMetadata.model_validate_json(metadata_path.read_text(encoding="utf-8"))
        calls.append(("generate", metadata.source_language))
        return [metadata_path.parent / "notes.md"]

    monkeypatch.setattr("video2post.cli.transcribe_audio", fake_transcribe)
    monkeypatch.setattr("video2post.cli.generate_outputs", fake_generate)

    result = runner.invoke(
        app,
        [
            "video",
            "https://www.youtube.com/watch?v=abc",
            "--output",
            str(tmp_path),
            "--lang",
            "zh",
            "--generate",
            "--targets",
            "notes",
        ],
    )

    assert result.exit_code == 0
    assert calls == [("transcribe", "zh"), ("generate", "zh")]


def test_video_bilibili_pipeline_can_generate_from_chinese_transcript(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(
        "video2post.cli.fetch_initial_video_metadata",
        lambda url, config=None: VideoMetadata(title="Bilibili Video"),
    )
    monkeypatch.setattr(
        "video2post.cli.prepare_audio",
        lambda metadata_path, config: metadata_path.parent / "audio.wav",
    )

    def fake_transcribe(metadata_path, config):
        calls.append(("transcribe", metadata_path.name))
        transcript = metadata_path.parent / "transcript.zh.md"
        transcript.write_text("中文整理稿", encoding="utf-8")
        return transcript

    def fake_generate(metadata_path, config, targets=None, cover_at=None, progress_callback=None):
        calls.append(("generate", tuple(targets or [])))
        return [metadata_path.parent / "notes.md"]

    monkeypatch.setattr("video2post.cli.transcribe_audio", fake_transcribe)
    monkeypatch.setattr("video2post.cli.generate_outputs", fake_generate)

    result = runner.invoke(
        app,
        [
            "video",
            "https://www.bilibili.com/video/BV123",
            "--output",
            str(tmp_path),
            "--generate",
            "--targets",
            "notes",
        ],
    )

    assert result.exit_code == 0
    assert calls == [("transcribe", "meta.json"), ("generate", ("notes",))]
    assert "Platform: bilibili" in result.output


def test_video_shows_friendly_youtube_cookie_guidance(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "video2post.cli.fetch_initial_video_metadata",
        lambda url, config=None: VideoMetadata(title="Needs Cookies"),
    )

    def fail_prepare(metadata_path, config):
        raise subprocess.CalledProcessError(
            1,
            ["yt-dlp"],
            stderr=(
                "ERROR: Sign in to confirm you’re not a bot. "
                "Use --cookies-from-browser or --cookies for the authentication."
            ),
        )

    monkeypatch.setattr("video2post.cli.prepare_audio", fail_prepare)

    result = runner.invoke(
        app,
        [
            "video",
            "https://www.youtube.com/watch?v=abc",
            "--output",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "YouTube download failed" in result.output
    assert "brew install node" in result.output
    assert "cookies_from_browser: chrome" in result.output


def test_video_shows_friendly_youtube_ejs_guidance(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "video2post.cli.fetch_initial_video_metadata",
        lambda url, config=None: VideoMetadata(title="Needs EJS"),
    )

    def fail_prepare(metadata_path, config):
        raise subprocess.CalledProcessError(
            1,
            ["yt-dlp"],
            stderr=(
                "WARNING: n challenge solving failed. "
                "ERROR: Requested format is not available. "
                "Only images are available for download."
            ),
        )

    monkeypatch.setattr("video2post.cli.prepare_audio", fail_prepare)

    result = runner.invoke(
        app,
        [
            "video",
            "https://www.youtube.com/watch?v=abc",
            "--output",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "JavaScript challenge" in result.output
    assert "node -v" in result.output
    assert 'yt-dlp[default]' in result.output
    assert "remote_components: ejs:github" in result.output


def test_task_list_command_lists_recent_tasks_from_output_directory(tmp_path):
    older_task = tmp_path / "2026-04-28-older-task"
    newer_task = tmp_path / "2026-04-29-newer-task"
    _write_task_metadata(older_task, status=TaskStatus.TRANSCRIBED)
    _write_task_metadata(newer_task, status=TaskStatus.TITLES_GENERATED)
    (newer_task / "audio.wav").write_bytes(b"audio")
    (newer_task / "transcript.zh.md").write_text("translated", encoding="utf-8")
    older_meta = older_task / "meta.json"
    newer_meta = newer_task / "meta.json"
    older_meta.touch()
    newer_meta.touch()

    result = runner.invoke(
        app,
        [
            "task",
            "list",
            "--output",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert "2026-04-29-newer-task" in lines[0]
    assert "titles_generated" in lines[0]
    assert "audio, transcript.zh" in lines[0]
    assert "2026-04-28-older-task" in lines[1]


def test_task_list_command_respects_limit(tmp_path):
    for index in range(3):
        task_dir = tmp_path / f"2026-04-2{index}-task-{index}"
        _write_task_metadata(task_dir, status=TaskStatus.CREATED)
        (task_dir / "meta.json").touch()

    result = runner.invoke(
        app,
        [
            "task",
            "list",
            "--output",
            str(tmp_path),
            "--limit",
            "2",
        ],
    )

    assert result.exit_code == 0
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert len(lines) == 2


def _write_task_metadata(
    tmp_path,
    *,
    status: TaskStatus,
    platform: str = "youtube",
    source_url: str = "https://www.youtube.com/watch?v=abc",
) -> Path:
    metadata = TaskMetadata(
        source_url=source_url,
        platform=platform,
        task_dir=tmp_path,
        status=status,
        video=VideoMetadata(title="Test Video"),
    )
    return write_metadata(metadata)


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


def test_format_command_for_task_uses_existing_artifacts(tmp_path):
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    (task_dir / "meta.json").write_text("{}", encoding="utf-8")
    (task_dir / "article.md").write_text("# Article", encoding="utf-8")

    result = runner.invoke(app, ["format", str(task_dir), "--platform", "wechat"])

    assert result.exit_code == 0
    assert (task_dir / "article.wechat.md").exists()
    assert (task_dir / "article.wechat.html").exists()


def test_draft_command_accepts_x_fetch_mode(monkeypatch):
    class FakeDraftResult:
        def __init__(self):
            self.task_dir = Path("drafts/2026-05-11-test")
            self.paths = [self.task_dir / "source.md"]

    calls = []

    def fake_generate_draft(
        content, config, *, mode, x_url=None, output_dir=None, title=None, progress_callback=None, x_fetch_mode="auto"
    ):
        calls.append(x_fetch_mode)
        return FakeDraftResult()

    monkeypatch.setattr("video2post.cli.generate_draft", fake_generate_draft)

    result = runner.invoke(
        app,
        ["draft", "--x-url", "https://x.com/big/status/1", "--x-fetch", "browser"],
    )

    assert result.exit_code == 0
    assert calls == ["browser"]
