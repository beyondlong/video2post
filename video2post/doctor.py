from __future__ import annotations

import importlib.util
import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from dotenv import load_dotenv


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


def collect_doctor_checks(
    *,
    env: dict[str, str] | None = None,
    resolver: Callable[[str], str | None] = shutil.which,
    finder: Callable[[str], object | None] = importlib.util.find_spec,
) -> list[DoctorCheck]:
    if env is None:
        load_dotenv(".env", override=False)
        env = dict(os.environ)

    checks = [
        _command_check("ffmpeg", resolver=resolver),
        _command_check("yt-dlp", resolver=resolver),
        _env_check("VIDEO2POST_LLM_API_KEY", env=env),
        _env_check("VIDEO2POST_LLM_BASE_URL", env=env),
        _env_check("VIDEO2POST_LLM_MODEL", env=env),
        _package_check("pydantic", finder=finder),
        _package_check("typer", finder=finder),
        _package_check("yaml", label="PyYAML", finder=finder),
        _package_check("httpx", finder=finder),
        _package_check("dotenv", label="python-dotenv", finder=finder),
        _package_check("faster_whisper", required=False, finder=finder),
        _package_check("funasr", required=False, finder=finder),
    ]
    return checks


def _command_check(name: str, *, resolver: Callable[[str], str | None]) -> DoctorCheck:
    path = resolver(name)
    if path:
        return DoctorCheck(name=name, status=DoctorStatus.OK, detail=path)
    return DoctorCheck(name=name, status=DoctorStatus.MISSING, detail="command not found")


def _env_check(name: str, *, env: dict[str, str]) -> DoctorCheck:
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
    )


def _package_check(
    module_name: str,
    *,
    label: str | None = None,
    required: bool = True,
    finder: Callable[[str], object | None],
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
        )
    return DoctorCheck(
        name=f"python:{module_name}",
        status=DoctorStatus.OPTIONAL,
        detail=f"{display_name} not installed",
        required=required,
    )
