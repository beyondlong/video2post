from typer.testing import CliRunner

from video2post.cli import app


def test_cli_help_shows_application_name():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "video2post" in result.output


def test_config_show_prints_effective_config():
    result = CliRunner().invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "output_dir" in result.output
    assert "openai_compatible" in result.output
