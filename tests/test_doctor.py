from collections.abc import Callable

from video2post.doctor import DoctorStatus, collect_doctor_checks


def test_collect_doctor_checks_reports_required_and_optional_items():
    env = {
        "VIDEO2POST_LLM_API_KEY": "key",
        "VIDEO2POST_LLM_BASE_URL": "https://api.example.com/v1",
        "VIDEO2POST_LLM_MODEL": "demo-model",
    }

    def resolver(name: str) -> str | None:
        return {
            "ffmpeg": "/opt/homebrew/bin/ffmpeg",
            "yt-dlp": "/opt/homebrew/bin/yt-dlp",
        }.get(name)

    def finder(name: str) -> object | None:
        available = {
            "pydantic",
            "typer",
            "yaml",
            "httpx",
            "dotenv",
            "faster_whisper",
        }
        return object() if name in available else None

    checks = collect_doctor_checks(env=env, resolver=resolver, finder=finder)

    assert checks[0].name == "ffmpeg"
    assert checks[0].status == DoctorStatus.OK
    assert checks[1].name == "yt-dlp"
    assert checks[1].status == DoctorStatus.OK
    assert any(check.name == ".env:VIDEO2POST_LLM_API_KEY" and check.status == DoctorStatus.OK for check in checks)
    assert any(check.name == "python:funasr" and check.status == DoctorStatus.OPTIONAL for check in checks)


def test_collect_doctor_checks_marks_missing_required_items():
    env: dict[str, str] = {}

    def resolver(name: str) -> str | None:
        return None

    def finder(name: str) -> object | None:
        return None

    checks = collect_doctor_checks(env=env, resolver=resolver, finder=finder)

    required_missing = [check for check in checks if check.required and check.status == DoctorStatus.MISSING]
    assert required_missing
    assert any(check.name == "ffmpeg" for check in required_missing)
    assert any(check.name == ".env:VIDEO2POST_LLM_API_KEY" for check in required_missing)
