import subprocess

from video2post.audio.ffmpeg import FfmpegAudioNormalizer


class FakeRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


def test_normalize_audio_builds_wav_16k_mono_command(tmp_path):
    runner = FakeRunner()
    normalizer = FfmpegAudioNormalizer(runner=runner)
    source = tmp_path / "source.m4a"
    target = tmp_path / "audio.wav"

    result = normalizer.normalize(source, target)

    assert result == target
    command, kwargs = runner.calls[0]
    assert command == [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(target),
    ]
    assert kwargs["check"] is True
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
