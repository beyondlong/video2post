# video2post 当前进度记录

> 更新时间：2026-04-29
>
> 当前开发分支：`codex/phase-0-cli-skeleton`
>
> 最新进度提交以 `git log` 为准。

本文档用于记录项目当前已经完成的能力、可测试效果和后续建议。`docs/development-plan.md` 继续作为开发计划使用，本文档记录真实落地进度。

## 当前整体状态

`video2post` 当前已经具备 YouTube 方向 CLI MVP 的核心骨架：

- 可以通过 CLI 创建视频处理任务。
- 可以获取 YouTube 视频元数据，并使用视频标题生成任务目录。
- 可以下载 YouTube 音频并标准化为 `audio.wav`。
- 可以接入 `faster-whisper` 生成英文转写稿。
- 可以通过 OpenAI-compatible LLM Provider 生成中文二创内容。
- 可以对已有任务做局部生成和断点续跑。
- 当前自动化测试通过：`41 passed`。

目前项目还处于个人自用 MVP 阶段，优先目标仍然是先把 YouTube 英文技术视频到中文二创内容的流程跑稳。

## 已完成能力

### 1. 项目基础骨架

已建立 Python CLI 项目结构：

```text
video2post/
  cli.py
  config.py
  pipeline.py
  models.py
  downloader/
  audio/
  asr/
  llm/
  writers/
tests/
docs/
prompts/
.env.example
config.example.yaml
pyproject.toml
README.md
```

已完成内容：

- Python 项目配置。
- Typer CLI 入口。
- Pydantic 配置模型。
- 基础测试目录。
- README 和需求文档。
- `.gitignore`，避免提交编译产物、缓存、中间输出和本地密钥。

### 2. 任务目录、元数据和状态模型

每个视频会生成独立任务目录，例如：

```text
outputs/
  2026-04-29-video-title/
    meta.json
    audio.wav
    transcript.en.md
    transcript.zh.md
    notes.md
    article.md
    script.md
    titles.md
```

已支持：

- 创建任务目录。
- 使用视频标题生成更友好的任务目录名。
- 写入和读取 `meta.json`。
- 记录任务状态。
- 记录视频标题、作者、时长等元数据。
- 记录失败阶段、错误信息和是否可重试。

当前任务状态包括：

```text
created
metadata_fetched
audio_downloaded
audio_normalized
transcribed
translated_or_cleaned
notes_generated
article_generated
script_generated
titles_generated
completed
failed
```

### 3. YouTube 音频下载与标准化

已接入：

- `yt-dlp`
- `ffmpeg`

当前流程：

```text
YouTube URL
  -> 获取视频元数据
  -> 下载压缩音频 source.webm / source.m4a
  -> 转换为 audio.wav
  -> 可选删除中间 source 文件
```

标准化音频格式：

```text
WAV
16kHz
mono
pcm_s16le
```

已经用真实 YouTube 链接测试过，最终 `audio.wav` 产物格式正确。

测试链接：

```text
https://www.youtube.com/watch?v=474wZZHoWN4
```

真实测试结果：

- 可以获取视频元数据。
- 可以生成标准化 `audio.wav`。
- `audio.wav` 为 16kHz、mono、`pcm_s16le`。
- 支持清理下载后的压缩源音频。

### 4. 中间文件清理

支持在音频标准化后删除下载的压缩源文件，只保留最终 `audio.wav`。

可用参数：

```bash
video2post process URL --cleanup-source
video2post process URL --keep-source
```

作用：

- `--cleanup-source`：删除 `source.webm` / `source.m4a` 等中间源文件，节省磁盘空间。
- `--keep-source`：保留下载的压缩源文件，方便调试或复查。

### 5. 英文 ASR 转写

已接入：

- `faster-whisper`

当前能力：

- 从 `audio.wav` 生成英文转写稿。
- 输出段落版 `transcript.en.md`。
- 额外输出 `transcript.segments.json`，保留原始 `start/end/text/language`。
- 支持跳过已存在转写文件。

当前统一 segment 结构：

```text
start
end
text
language
```

后续优化记录：

- 已讨论 `--fast` 模式，但当前决定暂缓实现。
- 后续可以把它做成“更快出稿”的模式，优先面向二创场景。
- 预期能力包括：更轻量的 ASR 模型、段落化英文稿、减少非必要产物、优先生成中文整理稿和笔记。

### 5.1 B 站中文转写基础支持

当前已经打通一版基础能力：

- B 站链接可以被识别为 `bilibili` 平台。
- B 站视频沿用现有下载和音频标准化链路。
- 转写阶段会按平台自动输出中文稿 `transcript.zh.md`。
- 同时保留 `transcript.segments.json` 原始 segment 数据。
- 后续 `notes/article/script/titles` 生成阶段可以直接使用中文稿作为输入。

当前边界：

- 这是一版“最小可用”实现，先复用现有 ASR 链路。
- `FunASR` Provider 已接入代码路径，但当前环境还没有完成真实 FunASR 端到端验收。
- 已完成一条真实 B 站链接的端到端验收，验证通过下载、音频标准化、中文转写、`notes.md` 和 `titles.md` 生成链路。

### 6. LLM Provider 与 Prompt 模板

已实现 OpenAI-compatible LLM Provider。

支持通过 `.env` 配置：

```bash
VIDEO2POST_LLM_API_KEY=
VIDEO2POST_LLM_BASE_URL=
VIDEO2POST_LLM_MODEL=
```

已验证 Minimax 配置：

```text
base_url=https://api.minimaxi.com/v1
model=MiniMax-M2.5
```

真实测试结果：

- 可以读取 `.env` 中的 LLM 配置。
- 可以调用 Minimax。
- 可以生成 `titles.md`。
- 已处理部分模型输出中的 `<think>...</think>` 内容，避免污染最终 Markdown。

当前 Prompt 模板：

```text
prompts/
  translation.md
  notes.md
  article.md
  script.md
  titles.md
```

### 7. YouTube 主链路 CLI

当前主命令：

```bash
video2post process URL
```

常用参数：

```bash
video2post process URL --output ./outputs
video2post process URL --generate --targets titles
video2post process URL --generate --targets article,script,titles
video2post process URL --cleanup-source
video2post process URL --no-transcribe
video2post process URL --no-download
```

当前 `process` 命令能力：

- 创建任务目录。
- 获取视频元数据。
- 下载和标准化音频。
- 可选执行英文 ASR。
- 可选执行 LLM 二创生成。
- 输出任务目录路径、平台和阶段产物路径。

### 8. 局部生成和断点续跑

已新增两个命令：

```bash
video2post generate TASK_DIR --targets article,script,titles
video2post retry TASK_DIR
```

`generate` 用途：

- 基于已有 `meta.json` 和 `transcript.en.md` 重新生成指定二创内容。
- 适合修改 Prompt 后重新生成文章、标题或口播稿。
- 不需要重新下载音频或重新 ASR。

`retry` 用途：

- 从已有任务目录继续缺失步骤。
- 如果已有 `audio.wav` 但缺少 `transcript.en.md`，会直接补转写。
- 如果加上 `--generate`，可以在补齐前置步骤后继续生成二创内容。

示例：

```bash
video2post generate ./outputs/2026-04-29-video-title --targets titles
video2post retry ./outputs/2026-04-29-video-title
video2post retry ./outputs/2026-04-29-video-title --generate --targets titles
```

## 当前可测试效果

### 1. 查看 CLI 是否可用

```bash
video2post --help
```

应能看到：

```text
process
generate
retry
config
```

### 2. 查看当前配置

```bash
video2post config show
```

应能看到默认配置，包括：

```text
output_dir
openai_compatible
```

### 3. 只创建任务目录，不下载

```bash
video2post process "https://www.youtube.com/watch?v=474wZZHoWN4" --no-download
```

可验证：

- 能识别 YouTube。
- 能获取视频标题。
- 能创建任务目录。
- 能生成 `meta.json`。

### 4. 下载并标准化音频

```bash
video2post process "https://www.youtube.com/watch?v=474wZZHoWN4" --no-transcribe --cleanup-source
```

可验证：

- 生成 `audio.wav`。
- 音频格式为 16kHz mono WAV。
- 中间 `source.webm` / `source.m4a` 被清理。

可使用 `ffprobe` 检查：

```bash
ffprobe TASK_DIR/audio.wav
```

重点检查：

```text
sample_rate=16000
channels=1
codec_name=pcm_s16le
```

### 5. 生成标题

已有 `transcript.en.md` 后，可以测试：

```bash
video2post generate TASK_DIR --targets titles
```

可验证：

- 读取 `.env` 中的大模型配置。
- 调用配置的大模型。
- 生成 `titles.md`。
- 更新 `meta.json` 中的 LLM 模型和任务状态。

### 6. 断点续跑

如果任务目录里已有 `audio.wav`，但没有 `transcript.en.md`：

```bash
video2post retry TASK_DIR
```

可验证：

- 不重新下载音频。
- 直接进入转写阶段。
- 生成 `transcript.en.md`。

如果已有转写稿：

```bash
video2post retry TASK_DIR --generate --targets titles
```

可验证：

- 不重复下载。
- 不重复转写。
- 只生成指定二创产物。

## 自动化测试状态

当前全量测试通过：

```bash
python3 -m pytest -q
# 41 passed
```

当前测试覆盖方向：

- CLI help。
- 配置读取和展示。
- 任务目录创建。
- 配置输出目录和命令行输出目录覆盖。
- 中间源文件清理参数。
- YouTube pipeline 编排。
- 跳过下载、跳过转写。
- LLM 生成命令。
- 断点续跑命令。
- 任务元数据读写。
- 音频下载与标准化逻辑。
- ASR 转写逻辑。
- LLM Prompt 和 Provider 逻辑。

## 当前限制

目前仍然没有完成：

- 长视频分块处理。
- B 站中文视频完整链路。
- 中文 ASR Provider。
- Web 工作台。
- 桌面应用。
- 批量任务队列。
- 自动发布到公众号、微博、小红书、B 站等平台。
- 素材库和检索。

阶段 7 已开始实现。当前已经具备基础长视频分块能力：当转写稿长度超过 `generation.chunk_max_chars` 时，系统会先输出 `chunks/` 和 `summaries/` 中间文件，再使用合并后的 chunk 摘要生成最终二创内容。重新生成最终稿件时，已有且非空的 chunk 摘要会被复用，避免重复调用 LLM。

当前仍需继续完善：

- 基于 ASR segment 的更精细切块。
- 针对超长视频的全局摘要和多级汇总。
- 更完整的真实长视频测试。
- `--fast` 模式和更激进的“快速出稿”链路优化。
- B 站真实样例验收和 `FunASR` 独立接入。

## 下一步建议

继续推进阶段 7：长视频分块处理。

建议顺序：

1. 基于 `transcript.en.md` 或 ASR segment 做文本切块。
2. 输出 `chunks/chunk-001.md` 等中间文件。
3. 为每个 chunk 生成局部摘要。
4. 输出 `summaries/chunk-001.summary.md` 等中间文件。
5. 基于局部摘要生成全局笔记。
6. 再基于全局笔记生成长文、口播稿和标题。

这样可以让 30-90 分钟技术视频更稳定，也更适合后续真实自媒体工作流。
