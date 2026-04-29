from pathlib import Path

from video2post.config import AppConfig, load_config


def test_default_config_uses_outputs_directory():
    config = AppConfig()

    assert config.app.output_dir == Path("outputs")
    assert config.app.keep_audio is True
    assert config.app.skip_existing is True


def test_load_config_merges_yaml_values(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
app:
  output_dir: custom_outputs
  keep_audio: false
llm:
  provider: openai_compatible
  model: test-model
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.app.output_dir == Path("custom_outputs")
    assert config.app.keep_audio is False
    assert config.app.skip_existing is True
    assert config.llm.model == "test-model"
