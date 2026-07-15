# AGENTS.md

This repository is `video2post`, a local CLI-first tool that turns YouTube/Bilibili technical videos into editable Chinese content drafts and publish-ready formats.

Use this file as the project-level operating guide for Codex and other coding agents.

## Project Shape

- Language/runtime: Python 3.11+.
- Package entrypoint: `video2post.cli:app` exposed as `video2post`.
- Main package: `video2post/`.
- Tests: `tests/`, run with `pytest`.
- Prompts: `prompts/`.
- Docs: `docs/`.
- Generated local outputs: `outputs/`, `outputs-check/`, `promo-video/`, task directories, audio/video files. Treat these as local artifacts unless the user explicitly asks to keep or publish them.

## Product Intent

The core workflow is:

```text
video URL
  -> metadata
  -> audio download and normalization
  -> ASR transcript
  -> Chinese translation or Chinese cleanup
  -> creator-oriented outputs
  -> publish-ready WeChat/X formats
```

The project currently prioritizes:

- YouTube English technical videos -> Chinese drafts.
- Bilibili / Chinese YouTube videos -> Chinese transcript and structured drafts.
- Creator-first outputs for X and WeChat.
- CLI usability, resumability, and inspectable local files.

## Important Commands

Prefer `python3 -m video2post.cli ...` when the local `video2post` command may not point at this checkout.

```bash
python3 -m video2post.cli --help
python3 -m video2post.cli process --help
python3 -m video2post.cli doctor
python3 -m video2post.cli config show
pytest -q
```

Common user-facing workflows:

```bash
# Fast creator draft. Auto-generates notes,x_article,x_thread,x_titles,publish_formats.
video2post process "VIDEO_URL" --fast --cleanup-source

# Chinese YouTube source.
video2post process "YOUTUBE_URL" --lang zh --fast --cleanup-source

# Full standard generation.
video2post process "VIDEO_URL" --generate --cleanup-source

# Regenerate selected outputs for an existing task.
video2post generate TASK_DIR --targets notes,x_article,x_thread,x_titles,publish_formats

# Rebuild publish formats only.
video2post generate TASK_DIR --targets publish_formats

# Format a standalone Markdown file.
video2post format article.md --platform wechat,x

# Format artifacts from a task directory.
video2post format-task TASK_DIR --source x_article --platform wechat,x
```

Full CLI usage lives in `docs/cli-usage.md`. Keep that document and CLI `--help` text aligned when changing command behavior.

## Generation Targets

Supported generation targets:

- `translation` -> `transcript.zh.md`
- `notes` -> `notes.md`
- `x_article` -> `x_article.md`
- `x_thread` -> `x_thread.md`
- `x_titles` -> `x_titles.md`
- `article` -> `article.md`
- `script` -> `script.md`
- `titles` -> `titles.md`
- `cover` -> `cover.jpg`, `cover.meta.json`
- `publish_formats` -> WeChat/X publish files

`process --fast` defaults to `notes,x_article,x_thread,x_titles,publish_formats` unless the user passes `--targets`.

Chinese sources skip `translation` by default. Chinese sources include Bilibili and YouTube with `--lang zh`.

## Publish Format Rules

Formatting lives in `video2post/formatters/`.

- WeChat outputs: `*.wechat.md`, `*.wechat.html`.
- X outputs: `*.x.md`, `*.x.txt`.
- WeChat HTML must preserve the warm inline public-account theme. Do not regress it to plain HTML.
- `format-task` source fallback:
  - WeChat: `article.md`, then `x_article.md`.
  - X: `x_article.md`, then `article.md`.
- `--rewrite` is currently a reserved LLM rewrite hook. Deterministic formatting is the normal path.

## Testing Expectations

Use focused tests first, then full tests before claiming completion.

```bash
pytest tests/test_cli.py -q
pytest tests/test_pipeline_generate.py -q
pytest tests/test_formatters_service.py tests/test_formatters_wechat.py tests/test_formatters_x_longform.py -q
pytest -q
```

Add or update tests for any behavior change. Important regression areas:

- CLI options and help text.
- `--fast` default target behavior.
- Chinese YouTube/Bilibili transcript routing.
- Long transcript chunking and global summary reuse.
- `publish_formats` file selection and WeChat inline styles.
- Failure status and retry metadata.

Pytest may warn that `.pytest_cache` cannot be written in restricted sandboxes. That warning alone is not a test failure.

## Development Guidelines

- Follow existing module boundaries before adding new ones.
- Keep CLI orchestration in `video2post/cli.py`.
- Keep pipeline state transitions and generation flow in `video2post/pipeline.py`.
- Keep error classification and fix suggestions in `video2post/diagnostics.py`.
- Keep environment checks and version detection in `video2post/doctor.py`.
- Keep platform-specific formatting in `video2post/formatters/`.
- Keep prompts in `prompts/`; prompt names should match generation target names unless there is a clear reason.
- Prefer structured parsing/helpers over ad hoc string rewrites for Markdown and metadata.
- Keep generated task outputs out of commits unless the user explicitly asks for fixtures.
- Pipeline errors should classify errors with `diagnostics.py` and pass `error_code` and `fix_suggestions` to `update_status`.

## Documentation Expectations

When changing CLI behavior, update all relevant places:

- `docs/cli-usage.md`
- `README.md`
- `docs/setup.md` when setup or common workflows change
- `docs/progress.md` for project status
- `docs/manual-checklist.md` when manual validation steps change

When adding a new feature that affects users, prefer examples over abstract descriptions.

## Network and Real Video Checks

Real YouTube/Bilibili runs may need network access, browser cookies, Node/EJS support, and local ASR dependencies. Do not assume those checks can run in a restricted environment.

For YouTube bot/login issues, prefer documenting or using config like:

```yaml
download:
  cookies_from_browser: chrome
  js_runtimes: node
  remote_components: ejs:github
```

Use `safari` instead of `chrome` if that is where the user is logged in.

## Git and Local Artifact Safety

- Do not stage `outputs-check/`, `outputs/`, `promo-video/`, downloaded media, generated audio, or task directories unless the user explicitly asks.
- Do not revert unrelated user changes.
- Before publishing changes, inspect `git status -sb` and stage only the intended source/docs/tests.
- Prefer draft PRs unless the user asks to merge directly.

## Definition of Done

A change is ready to report as complete when:

- The requested behavior is implemented.
- Relevant docs/help text are updated.
- Focused tests pass.
- `pytest -q` passes, or any inability to run it is clearly explained.
- The final response mentions the files changed and validation performed.
