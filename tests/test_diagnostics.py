import subprocess

from video2post.diagnostics import (
    DiagnosticResult,
    classify_asr_error,
    classify_download_error,
    classify_ffmpeg_error,
    classify_llm_error,
    format_error_for_cli,
)
from video2post.llm.openai_compatible import LlmProviderError
from video2post.models import ErrorCode


def test_classify_youtube_cookie_auth_error():
    error = subprocess.CalledProcessError(
        1, ["yt-dlp"],
        stderr="ERROR: Sign in to confirm you're not a bot. Use --cookies-from-browser",
    )
    result = classify_download_error(error, platform="youtube")

    assert result.error_code == ErrorCode.DOWNLOAD_COOKIE_AUTH
    assert result.retryable is True
    assert any("cookies_from_browser" in s for s in result.fix_suggestions)


def test_classify_youtube_js_challenge_error():
    error = subprocess.CalledProcessError(
        1, ["yt-dlp"],
        stderr="WARNING: n challenge solving failed. ERROR: Requested format is not available.",
    )
    result = classify_download_error(error, platform="youtube")

    assert result.error_code == ErrorCode.DOWNLOAD_JS_CHALLENGE
    assert result.retryable is True
    assert any("yt-dlp" in s for s in result.fix_suggestions)


def test_classify_video_unavailable_error():
    error = subprocess.CalledProcessError(
        1, ["yt-dlp"],
        stderr="ERROR: Video unavailable",
    )
    result = classify_download_error(error, platform="youtube")

    assert result.error_code == ErrorCode.DOWNLOAD_VIDEO_UNAVAILABLE
    assert result.retryable is False


def test_classify_network_error():
    error = subprocess.CalledProcessError(
        1, ["yt-dlp"],
        stderr="ERROR: unable to download webpage: <urlopen error [Errno 8] timed out>",
    )
    result = classify_download_error(error, platform="youtube")

    assert result.error_code == ErrorCode.DOWNLOAD_NETWORK
    assert result.retryable is True


def test_classify_unknown_download_error():
    error = subprocess.CalledProcessError(
        1, ["yt-dlp"],
        stderr="ERROR: something unexpected happened",
    )
    result = classify_download_error(error, platform="bilibili")

    assert result.error_code == ErrorCode.UNKNOWN
    assert result.retryable is True
    assert any("yt-dlp" in s for s in result.fix_suggestions)


def test_classify_ffmpeg_not_found():
    error = subprocess.CalledProcessError(
        127, ["ffmpeg"],
        stderr="ffmpeg: not found",
    )
    result = classify_ffmpeg_error(error)

    assert result.error_code == ErrorCode.FFMPEG_NOT_FOUND
    assert result.retryable is False
    assert any("install ffmpeg" in s.lower() for s in result.fix_suggestions)


def test_classify_ffmpeg_conversion_failed():
    error = subprocess.CalledProcessError(
        1, ["ffmpeg"],
        stderr="Invalid data found when processing input",
    )
    result = classify_ffmpeg_error(error)

    assert result.error_code == ErrorCode.FFMPEG_CONVERSION_FAILED
    assert result.retryable is True


def test_classify_asr_quality_error():
    error = RuntimeError("ASR output too repetitive")
    result = classify_asr_error(error, is_quality_error=True)

    assert result.error_code == ErrorCode.ASR_QUALITY_CHECK_FAILED
    assert result.retryable is True
    assert any("quality" in s.lower() for s in result.fix_suggestions)


def test_classify_asr_import_error():
    error = ImportError("No module named 'faster_whisper'")
    result = classify_asr_error(error)

    assert result.error_code == ErrorCode.ASR_MODEL_NOT_INSTALLED
    assert result.retryable is False
    assert any("pip install" in s for s in result.fix_suggestions)


def test_classify_asr_generic_error():
    error = RuntimeError("CUDA out of memory")
    result = classify_asr_error(error)

    assert result.error_code == ErrorCode.ASR_TRANSCRIPTION_FAILED
    assert result.retryable is True


def test_classify_llm_missing_api_key():
    error = RuntimeError("Missing VIDEO2POST_LLM_API_KEY environment variable.")
    result = classify_llm_error(error)

    assert result.error_code == ErrorCode.LLM_MISSING_CONFIG
    assert result.retryable is False


def test_classify_llm_missing_base_url():
    error = RuntimeError("Missing llm.base_url configuration.")
    result = classify_llm_error(error)

    assert result.error_code == ErrorCode.LLM_MISSING_CONFIG
    assert result.retryable is False


def test_classify_llm_auth_failed():
    error = LlmProviderError(
        "LLM request failed with HTTP 401",
        status_code=401,
        response_body='{"error": "invalid_api_key"}',
    )
    result = classify_llm_error(error)

    assert result.error_code == ErrorCode.LLM_AUTH_FAILED
    assert result.retryable is False


def test_classify_llm_rate_limit():
    error = LlmProviderError(
        "LLM request failed with HTTP 429",
        status_code=429,
        response_body='{"error": "rate_limit_exceeded"}',
    )
    result = classify_llm_error(error)

    assert result.error_code == ErrorCode.LLM_RATE_LIMIT
    assert result.retryable is True


def test_classify_llm_sensitive_content():
    error = LlmProviderError(
        "LLM request failed with HTTP 422",
        status_code=422,
        response_body='{"error":{"message":"output new_sensitive (1027)"}}',
        provider_error_message="output new_sensitive (1027)",
    )
    result = classify_llm_error(error)

    assert result.error_code == ErrorCode.LLM_CONTENT_FILTERED
    assert result.retryable is True


def test_classify_llm_timeout():
    error = RuntimeError("Request timed out after 300 seconds")
    result = classify_llm_error(error)

    assert result.error_code == ErrorCode.LLM_TIMEOUT
    assert result.retryable is True


def test_classify_llm_generic_provider_error():
    error = LlmProviderError(
        "LLM request failed with HTTP 500",
        status_code=500,
        response_body="Internal Server Error",
    )
    result = classify_llm_error(error)

    assert result.error_code == ErrorCode.LLM_PROVIDER_ERROR
    assert result.retryable is True


def test_format_error_for_cli_includes_all_sections():
    output = format_error_for_cli(
        ErrorCode.DOWNLOAD_COOKIE_AUTH,
        "Sign in to confirm you're not a bot",
        ["Install node", "Add cookies config"],
        stage="download",
        retryable=True,
        task_dir="/tmp/test-task",
    )

    assert "Error: YouTube requires browser cookies" in output
    assert "Stage: download" in output
    assert "Detail:" in output
    assert "How to fix:" in output
    assert "1. Install node" in output
    assert "2. Add cookies config" in output
    assert "retryable" in output.lower()
    assert "/tmp/test-task" in output


def test_format_error_for_cli_non_retryable_omits_retry_hint():
    output = format_error_for_cli(
        ErrorCode.FFMPEG_NOT_FOUND,
        "ffmpeg not found",
        ["Install ffmpeg"],
        retryable=False,
    )

    assert "Error:" in output
    assert "retryable" not in output.lower()


def test_format_error_for_cli_empty_suggestions():
    output = format_error_for_cli(
        ErrorCode.UNKNOWN,
        "something went wrong",
        [],
    )

    assert "Error:" in output
    assert "How to fix:" not in output


def test_bilibili_cookie_error_uses_generic_classification():
    error = subprocess.CalledProcessError(
        1, ["yt-dlp"],
        stderr="ERROR: Sign in to confirm you're not a bot.",
    )
    result = classify_download_error(error, platform="bilibili")

    assert result.error_code != ErrorCode.DOWNLOAD_COOKIE_AUTH
