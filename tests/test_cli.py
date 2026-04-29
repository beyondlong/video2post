from pathlib import Path

from typer.testing import CliRunner

from video2post.cli import app
from video2post.models import TaskMetadata, TaskStatus, VideoMetadata
from video2post.writers.metadata import write_metadata


runner = CliRunner()


def test_cli_help_shows_application_name():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "video2post" in result.output


def test_config_show_prints_effective_config():
    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "output_dir" in result.output
    assert "openai_compatible" in result.output


def test_process_uses_configured_output_directory(tmp_path):
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
            "process",
            "https://www.youtube.com/watch?v=abc",
            "--config",
            str(config_file),
            "--no-download",
        ],
    )

    assert result.exit_code == 0
    assert str(configured_output) in result.output
    assert list(configured_output.glob("*/meta.json"))


def test_process_output_option_overrides_config(tmp_path):
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
            "process",
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


def test_process_cleanup_source_option_overrides_config(tmp_path):
    result = runner.invoke(
        app,
        [
            "process",
            "https://www.youtube.com/watch?v=abc",
            "--output",
            str(tmp_path),
            "--cleanup-source",
            "--no-download",
        ],
    )

    assert result.exit_code == 0
    assert "Source cleanup: enabled" in result.output


def test_process_can_run_full_pipeline_with_generate(monkeypatch, tmp_path):
    calls = []

    def fake_fetch_metadata(url):
        calls.append(("fetch_metadata", url))
        from video2post.models import VideoMetadata

        return VideoMetadata(title="Real Video Title")

    def fake_prepare(metadata_path, config):
        calls.append(("audio", metadata_path.name))
        return metadata_path.parent / "audio.wav"

    def fake_transcribe(metadata_path, config):
        calls.append(("transcribe", metadata_path.name))
        return metadata_path.parent / "transcript.en.md"

    def fake_generate(metadata_path, config, targets=None):
        calls.append(("generate", tuple(targets or [])))
        return [metadata_path.parent / "titles.md"]

    monkeypatch.setattr("video2post.cli.fetch_initial_video_metadata", fake_fetch_metadata)
    monkeypatch.setattr("video2post.cli.prepare_audio", fake_prepare)
    monkeypatch.setattr("video2post.cli.transcribe_audio", fake_transcribe)
    monkeypatch.setattr("video2post.cli.generate_outputs", fake_generate)

    result = runner.invoke(
        app,
        [
            "process",
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
        ("fetch_metadata", "https://www.youtube.com/watch?v=abc"),
        ("audio", "meta.json"),
        ("transcribe", "meta.json"),
        ("generate", ("titles",)),
    ]
    assert list(tmp_path.glob("*/meta.json"))[0].parent.name.endswith("real-video-title")
    assert "Transcript:" in result.output
    assert "Generated:" in result.output


def test_process_can_skip_transcribe_and_generate(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(
        "video2post.cli.fetch_initial_video_metadata",
        lambda url: calls.append("fetch_metadata") or None,
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
            "process",
            "https://www.youtube.com/watch?v=abc",
            "--output",
            str(tmp_path),
            "--no-transcribe",
            "--no-generate",
        ],
    )

    assert result.exit_code == 0
    assert calls == ["fetch_metadata", "audio"]


def test_generate_command_regenerates_selected_targets(monkeypatch, tmp_path):
    metadata_path = _write_task_metadata(tmp_path, status=TaskStatus.TRANSCRIBED)
    calls = []

    def fake_generate(metadata_path_arg, config, targets=None):
        calls.append((metadata_path_arg, tuple(targets or [])))
        return [metadata_path_arg.parent / "titles.md"]

    monkeypatch.setattr("video2post.cli.generate_outputs", fake_generate)

    result = runner.invoke(
        app,
        [
            "generate",
            str(tmp_path),
            "--targets",
            "titles",
        ],
    )

    assert result.exit_code == 0
    assert calls == [(metadata_path, ("titles",))]
    assert "Generated:" in result.output


def test_retry_transcribes_when_audio_exists_but_transcript_is_missing(monkeypatch, tmp_path):
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

    result = runner.invoke(app, ["retry", str(tmp_path)])

    assert result.exit_code == 0
    assert calls == [("transcribe", metadata_path)]
    assert "Transcript:" in result.output


def test_retry_can_generate_after_transcription(monkeypatch, tmp_path):
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
        lambda metadata_path_arg, config, targets=None: calls.append(
            ("generate", tuple(targets or []))
        )
        or [metadata_path_arg.parent / "titles.md"],
    )

    result = runner.invoke(
        app,
        [
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


def _write_task_metadata(tmp_path, *, status: TaskStatus) -> Path:
    metadata = TaskMetadata(
        source_url="https://www.youtube.com/watch?v=abc",
        platform="youtube",
        task_dir=tmp_path,
        status=status,
        video=VideoMetadata(title="Test Video"),
    )
    return write_metadata(metadata)
