"""Error classification and fix suggestion engine.

Classifies pipeline errors into structured error codes with actionable
fix suggestions that help users self-recover from common failures.
"""

from __future__ import annotations

import subprocess
from typing import NamedTuple

from video2post.models import ErrorCode


class DiagnosticResult(NamedTuple):
    error_code: ErrorCode
    retryable: bool
    fix_suggestions: list[str]


def classify_download_error(
    error: subprocess.CalledProcessError,
    *,
    platform: str,
) -> DiagnosticResult:
    stderr = (error.stderr or "").lower()

    if platform == "youtube":
        if _matches_cookie_auth(stderr):
            return DiagnosticResult(
                error_code=ErrorCode.DOWNLOAD_COOKIE_AUTH,
                retryable=True,
                fix_suggestions=[
                    "Install a JavaScript runtime: brew install node",
                    "Add to config.yaml:\n  download:\n    cookies_from_browser: chrome",
                    "Use safari instead of chrome if that is where you are logged into YouTube.",
                    "Run `video2post doctor` to verify setup.",
                ],
            )
        if _matches_js_challenge(stderr):
            return DiagnosticResult(
                error_code=ErrorCode.DOWNLOAD_JS_CHALLENGE,
                retryable=True,
                fix_suggestions=[
                    "Confirm Node is installed: node -v",
                    'Upgrade yt-dlp with EJS support: python3 -m pip install -U "yt-dlp[default]"',
                    "Add to config.yaml:\n  download:\n    remote_components: ejs:github",
                    "Keep browser cookies enabled if needed.",
                ],
            )

    if _matches_video_unavailable(stderr):
        return DiagnosticResult(
            error_code=ErrorCode.DOWNLOAD_VIDEO_UNAVAILABLE,
            retryable=False,
            fix_suggestions=[
                "Verify the video URL is correct and the video is publicly accessible.",
                f"For {platform} videos, check if the video requires login or is region-restricted.",
            ],
        )

    if _matches_network_error(stderr):
        return DiagnosticResult(
            error_code=ErrorCode.DOWNLOAD_NETWORK,
            retryable=True,
            fix_suggestions=[
                "Check your internet connection.",
                "If behind a proxy, configure proxy settings.",
                "Try again in a few minutes.",
            ],
        )

    return DiagnosticResult(
        error_code=ErrorCode.UNKNOWN,
        retryable=True,
        fix_suggestions=[
            f"yt-dlp stderr: {(error.stderr or str(error))[:200]}",
            "Try updating yt-dlp: python3 -m pip install -U yt-dlp",
            "Run `video2post doctor` to check dependencies.",
        ],
    )


def classify_ffmpeg_error(
    error: subprocess.CalledProcessError,
) -> DiagnosticResult:
    stderr = (error.stderr or "").lower()
    cmd_str = str(error.cmd) if error.cmd else ""

    if "not found" in stderr or "no such file or directory" in cmd_str.lower():
        return DiagnosticResult(
            error_code=ErrorCode.FFMPEG_NOT_FOUND,
            retryable=False,
            fix_suggestions=[
                "Install ffmpeg: brew install ffmpeg (macOS) or apt install ffmpeg (Linux).",
                "Run `video2post doctor` to verify installation.",
            ],
        )

    return DiagnosticResult(
        error_code=ErrorCode.FFMPEG_CONVERSION_FAILED,
        retryable=True,
        fix_suggestions=[
            f"ffmpeg stderr: {(error.stderr or str(error))[:200]}",
            "The source audio/video file may be corrupt or in an unsupported format.",
            "Try downloading the source again: video2post task retry TASK_DIR",
        ],
    )


def classify_asr_error(
    error: Exception,
    *,
    is_quality_error: bool = False,
) -> DiagnosticResult:
    message = str(error).lower()

    if is_quality_error:
        return DiagnosticResult(
            error_code=ErrorCode.ASR_QUALITY_CHECK_FAILED,
            retryable=True,
            fix_suggestions=[
                "The ASR output is low quality (repetitive or wrong language).",
                "Try a different ASR model in config.yaml:\n  asr:\n    english_provider: faster_whisper\n    faster_whisper_model: medium",
                "For Chinese audio, ensure chinese_provider is set correctly.",
                "Check that the audio file is not silent or corrupt.",
            ],
        )

    if "no module named" in message or "import" in message:
        return DiagnosticResult(
            error_code=ErrorCode.ASR_MODEL_NOT_INSTALLED,
            retryable=False,
            fix_suggestions=[
                'Install the ASR dependency: pip install "video2post[asr]" for faster-whisper.',
                'For Apple Silicon: pip install "video2post[asr-mlx]" for mlx-whisper.',
                'For Chinese ASR: pip install "video2post[asr-chinese]" for FunASR.',
                "Run `video2post doctor` to check which ASR backends are available.",
            ],
        )

    return DiagnosticResult(
        error_code=ErrorCode.ASR_TRANSCRIPTION_FAILED,
        retryable=True,
        fix_suggestions=[
            f"ASR error: {str(error)[:200]}",
            "Try a different ASR model or check audio quality.",
            "Run `video2post doctor` to verify ASR dependencies.",
        ],
    )


def classify_llm_error(error: Exception) -> DiagnosticResult:
    message = str(error).lower()

    if "missing video2post_llm_api_key" in message:
        return DiagnosticResult(
            error_code=ErrorCode.LLM_MISSING_CONFIG,
            retryable=False,
            fix_suggestions=[
                "Set VIDEO2POST_LLM_API_KEY in your .env file.",
                "Run `video2post doctor` to verify LLM configuration.",
            ],
        )

    if "missing llm.base_url" in message or "missing llm.model" in message:
        return DiagnosticResult(
            error_code=ErrorCode.LLM_MISSING_CONFIG,
            retryable=False,
            fix_suggestions=[
                "Configure LLM settings in .env or config.yaml:",
                "  VIDEO2POST_LLM_BASE_URL=https://api.openai.com/v1",
                "  VIDEO2POST_LLM_MODEL=gpt-4o",
                "Run `video2post doctor` to verify LLM configuration.",
            ],
        )

    from video2post.llm.openai_compatible import LlmProviderError

    if isinstance(error, LlmProviderError):
        return _classify_llm_provider_error(error)

    if "timeout" in message or "timed out" in message:
        return DiagnosticResult(
            error_code=ErrorCode.LLM_TIMEOUT,
            retryable=True,
            fix_suggestions=[
                "LLM request timed out. This often happens with long transcripts.",
                "Increase timeout in config.yaml:\n  llm:\n    request_timeout_seconds: 600",
                "Or reduce chunk size:\n  generation:\n    chunk_max_chars: 4000",
            ],
        )

    return DiagnosticResult(
        error_code=ErrorCode.LLM_PROVIDER_ERROR,
        retryable=True,
        fix_suggestions=[
            f"LLM error: {str(error)[:200]}",
            "Check your LLM provider status and API key.",
            "Run `video2post doctor` to verify configuration.",
        ],
    )


def _classify_llm_provider_error(error) -> DiagnosticResult:
    status = error.status_code or 0
    body = (error.response_body or "").lower()
    provider_msg = (error.provider_error_message or "").lower()

    if status == 401 or status == 403:
        return DiagnosticResult(
            error_code=ErrorCode.LLM_AUTH_FAILED,
            retryable=False,
            fix_suggestions=[
                "LLM API authentication failed (HTTP {}).".format(status),
                "Verify VIDEO2POST_LLM_API_KEY is correct in .env.",
                "Check if the API key has expired or reached its spending limit.",
            ],
        )

    if status == 429:
        return DiagnosticResult(
            error_code=ErrorCode.LLM_RATE_LIMIT,
            retryable=True,
            fix_suggestions=[
                "LLM API rate limit exceeded.",
                "Wait a few minutes and retry: video2post task retry TASK_DIR --generate",
                "Consider using a model with higher rate limits.",
            ],
        )

    if "sensitive" in body or "sensitive" in provider_msg:
        return DiagnosticResult(
            error_code=ErrorCode.LLM_CONTENT_FILTERED,
            retryable=True,
            fix_suggestions=[
                "Content was flagged by the LLM provider's safety filter.",
                "The pipeline will attempt a local extractive fallback automatically.",
                "If this persists, try a different LLM model or provider.",
            ],
        )

    return DiagnosticResult(
        error_code=ErrorCode.LLM_PROVIDER_ERROR,
        retryable=True,
        fix_suggestions=[
            "LLM request failed (HTTP {}).".format(status),
            "Retry with: video2post task retry TASK_DIR --generate",
            "Check provider status and configuration.",
        ],
    )


def format_error_for_cli(
    error_code: ErrorCode,
    message: str,
    fix_suggestions: list[str],
    *,
    stage: str = "",
    retryable: bool = False,
    task_dir: str = "",
) -> str:
    lines: list[str] = []
    label = _error_code_label(error_code)
    lines.append(f"Error: {label}")
    if stage:
        lines.append(f"Stage: {stage}")
    lines.append(f"Detail: {message[:500]}")
    lines.append("")

    if fix_suggestions:
        lines.append("How to fix:")
        for index, suggestion in enumerate(fix_suggestions, 1):
            lines.append(f"  {index}. {suggestion}")
        lines.append("")

    if retryable:
        retry_cmd = f"video2post task retry {task_dir}" if task_dir else "video2post task retry TASK_DIR"
        lines.append(f"This error is retryable. Run: {retry_cmd}")

    return "\n".join(lines)


_ERROR_CODE_LABELS: dict[ErrorCode, str] = {
    ErrorCode.UNKNOWN: "Unknown error",
    ErrorCode.DOWNLOAD_COOKIE_AUTH: "YouTube requires browser cookies for authentication",
    ErrorCode.DOWNLOAD_JS_CHALLENGE: "YouTube JavaScript challenge failed",
    ErrorCode.DOWNLOAD_VIDEO_UNAVAILABLE: "Video is unavailable",
    ErrorCode.DOWNLOAD_NETWORK: "Network connection error",
    ErrorCode.FFMPEG_NOT_FOUND: "ffmpeg is not installed",
    ErrorCode.FFMPEG_CONVERSION_FAILED: "Audio/video conversion failed",
    ErrorCode.ASR_MODEL_NOT_INSTALLED: "ASR model dependency is not installed",
    ErrorCode.ASR_TRANSCRIPTION_FAILED: "Speech recognition failed",
    ErrorCode.ASR_QUALITY_CHECK_FAILED: "Transcript quality check failed",
    ErrorCode.LLM_AUTH_FAILED: "LLM API authentication failed",
    ErrorCode.LLM_MISSING_CONFIG: "LLM configuration is incomplete",
    ErrorCode.LLM_RATE_LIMIT: "LLM API rate limit exceeded",
    ErrorCode.LLM_TIMEOUT: "LLM request timed out",
    ErrorCode.LLM_CONTENT_FILTERED: "Content flagged by LLM safety filter",
    ErrorCode.LLM_PROVIDER_ERROR: "LLM provider error",
    ErrorCode.LLM_REFUSAL: "LLM refused to process the content",
    ErrorCode.FILE_NOT_FOUND: "Required file not found",
    ErrorCode.INVALID_INPUT: "Invalid input",
}


def _error_code_label(code: ErrorCode) -> str:
    return _ERROR_CODE_LABELS.get(code, code.value)


def _matches_cookie_auth(stderr: str) -> bool:
    return (
        "sign in to confirm you're not a bot" in stderr
        or "sign in to confirm you\u2019re not a bot" in stderr
        or "--cookies-from-browser" in stderr
    )


def _matches_js_challenge(stderr: str) -> bool:
    return (
        "n challenge solving failed" in stderr
        or "requested format is not available" in stderr
        or "only images are available for download" in stderr
    )


def _matches_video_unavailable(stderr: str) -> bool:
    return (
        "video unavailable" in stderr
        or "this video is not available" in stderr
        or "this video has been removed" in stderr
        or "this video is private" in stderr
    )


def _matches_network_error(stderr: str) -> bool:
    return (
        "unable to download" in stderr
        and ("urlopen error" in stderr or "connection" in stderr or "timed out" in stderr)
    )
