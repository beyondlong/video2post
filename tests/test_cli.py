from typer.testing import CliRunner

from video2post.cli import app


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
