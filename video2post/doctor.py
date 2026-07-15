from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from video2post.env import load_video2post_dotenv


class DoctorStatus(StrEnum):
    OK = "ok"
    MISSING = "missing"
    OPTIONAL = "optional"


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: DoctorStatus
    detail: str
    required: bool = True
    fix_hint: str = ""


Runner = Callable[..., subprocess.CompletedProcess[str]]


def collect_doctor_checks(
    *,
    env: dict[str, str] | None = None,
    resolver: Callable[[str], str | None] = shutil.which,
    finder: Callable[[str], object | None] = importlib.util.find_spec,
    runner: Runner = subprocess.run,
    config_path: Path | str | None = None,
) -> list[DoctorCheck]:
    if env is None:
        load_video2post_dotenv()
        env = dict(os.environ)

    checks = [
        _command_check_with_version("ffmpeg", resolver=resolver, runner=runner,
                                     fix_hint="brew install ffmpeg (macOS) or apt install ffmpeg (Linux)"),
        _command_check_with_version("yt-dlp", resolver=resolver, runner=runner,
                                     fix_hint="python3 -m pip install -U yt-dlp"),
        _command_check("node", resolver=resolver, required=False,
                       fix_hint="brew install node (macOS) — needed for YouTube JS challenges"),
        _env_check("VIDEO2POST_LLM_API_KEY", env=env,
                   fix_hint="Add VIDEO2POST_LLM_API_KEY=your-key to .env"),
        _env_check("VIDEO2POST_LLM_BASE_URL", env=env,
                   fix_hint="Add VIDEO2POST_LLM_BASE_URL=https://api.openai.com/v1 to .env"),
        _env_check("VIDEO2POST_LLM_MODEL", env=env,
                   fix_hint="Add VIDEO2POST_LLM_MODEL=gpt-4o to .env"),
        _package_check("pydantic", finder=finder),
        _package_check("typer", finder=finder),
        _package_check("yaml", label="PyYAML", finder=finder),
        _package_check("httpx", finder=finder),
        _package_check("dotenv", label="python-dotenv", finder=finder),
        _package_check("faster_whisper", required=False, finder=finder,
                       fix_hint='pip install "video2post[asr]"'),
        _package_check("mlx_whisper", required=False, finder=finder,
                       fix_hint='pip install "video2post[asr-mlx]" (Apple Silicon only)'),
        _package_check("funasr", required=False, finder=finder,
                       fix_hint='pip install "video2post[asr-chinese]"'),
        _config_check(config_path),
    ]
    return checks


def _command_check(
    name: str,
    *,
    resolver: Callable[[str], str | None],
    required: bool = True,
    fix_hint: str = "",
) -> DoctorCheck:
    path = resolver(name)
    if path:
        return DoctorCheck(name=name, status=DoctorStatus.OK, detail=path, required=required)
    if not required:
        return DoctorCheck(name=name, status=DoctorStatus.OPTIONAL,
                          detail="not installed", required=False, fix_hint=fix_hint)
    return DoctorCheck(name=name, status=DoctorStatus.MISSING,
                      detail="command not found", fix_hint=fix_hint)


def _command_check_with_version(
    name: str,
    *,
    resolver: Callable[[str], str | None],
    runner: Runner,
    fix_hint: str = "",
) -> DoctorCheck:
    path = resolver(name)
    if not path:
        return DoctorCheck(name=name, status=DoctorStatus.MISSING,
                          detail="command not found", fix_hint=fix_hint)
    version = _get_command_version(name, runner=runner)
    detail = f"{path} ({version})" if version else path
    return DoctorCheck(name=name, status=DoctorStatus.OK, detail=detail)


def _get_command_version(name: str, *, runner: Runner) -> str:
    try:
        result = runner(
            [name, "--version"],
            capture_output=True, text=True, timeout=5,
        )
        output = (result.stdout or result.stderr or "").strip()
        first_line = output.splitlines()[0] if output else ""
        return first_line[:80]
    except (subprocess.SubprocessError, OSError, IndexError):
        return ""


def _env_check(name: str, *, env: dict[str, str], fix_hint: str = "") -> DoctorCheck:
    value = env.get(name, "").strip()
    if value:
        return DoctorCheck(
            name=f".env:{name}",
            status=DoctorStatus.OK,
            detail="configured",
        )
    return DoctorCheck(
        name=f".env:{name}",
        status=DoctorStatus.MISSING,
        detail="missing",
        fix_hint=fix_hint,
    )


def _package_check(
    module_name: str,
    *,
    label: str | None = None,
    required: bool = True,
    finder: Callable[[str], object | None],
    fix_hint: str = "",
) -> DoctorCheck:
    display_name = label or module_name
    found = finder(module_name) is not None
    if found:
        return DoctorCheck(
            name=f"python:{module_name}",
            status=DoctorStatus.OK,
            detail=f"{display_name} importable",
            required=required,
        )
    if required:
        return DoctorCheck(
            name=f"python:{module_name}",
            status=DoctorStatus.MISSING,
            detail=f"{display_name} not installed",
            required=required,
            fix_hint=fix_hint,
        )
    return DoctorCheck(
        name=f"python:{module_name}",
        status=DoctorStatus.OPTIONAL,
        detail=f"{display_name} not installed",
        required=required,
        fix_hint=fix_hint,
    )


def _config_check(config_path: Path | str | None) -> DoctorCheck:
    target = Path(config_path) if config_path else Path("config.yaml")
    if target.exists():
        try:
            import yaml
            content = yaml.safe_load(target.read_text(encoding="utf-8"))
            if isinstance(content, dict):
                return DoctorCheck(
                    name="config.yaml",
                    status=DoctorStatus.OK,
                    detail=str(target),
                    required=False,
                )
            return DoctorCheck(
                name="config.yaml",
                status=DoctorStatus.OPTIONAL,
                detail="config file exists but is not a valid YAML mapping",
                required=False,
                fix_hint="Ensure config.yaml contains valid YAML. See config.example.yaml.",
            )
        except Exception as exc:
            return DoctorCheck(
                name="config.yaml",
                status=DoctorStatus.OPTIONAL,
                detail=f"config file parse error: {exc}",
                required=False,
                fix_hint="Fix YAML syntax in config.yaml. See config.example.yaml.",
            )
    return DoctorCheck(
        name="config.yaml",
        status=DoctorStatus.OPTIONAL,
        detail="not found (defaults will be used)",
        required=False,
        fix_hint="Copy config.example.yaml to config.yaml and customize.",
    )
