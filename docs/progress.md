# video2post 当前进度记录

> 更新时间：2026-05-01
>
> 当前开发分支：`codex/phase-0-cli-skeleton`
>
> 最新进度提交以 `git log` 为准。

本文档用于记录项目当前已经完成的能力、可测试效果和后续建议。`docs/development-plan.md` 继续作为开发计划使用，本文档记录真实落地进度。

当前阶段 9 已开始补“固定样例与手工回归基线”：

- 固定样例清单：`docs/samples.md`
- 内置样例命令：`video2post samples`
- 手工回归检查表：`docs/manual-checklist.md`
- 真实验收产物对照：`docs/test-fixtures.md`

## 当前整体状态

`video2post` 当前已经具备 YouTube 方向 CLI MVP 的核心骨架：

- 可以通过 CLI 创建视频处理任务。
- 可以获取 YouTube 视频元数据，并使用视频标题生成任务目录。
- 可以下载 YouTube 音频并标准化为 `audio.wav`。
- 可以接入 `faster-whisper` 生成英文转写稿。
- 可以通过 OpenAI-compatible LLM Provider 生成中文二创内容。
- 可以生成适合 X 平台发布的长文、thread、标题候选和封面图。
- 可以对已有任务做局部生成和断点续跑。
- 当前自动化测试通过：以最新 `pytest` 结果为准。

目前项目还处于个人自用 MVP 阶段，优先目标仍然是先把 YouTube 英文技术视频到适合 X 平台发布的中文内容流程跑稳。

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
- 当前默认英文 ASR 模型已调整为 `faster-whisper base`，优先改善本地自测速度。

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
- `FunASR` Provider 已接入代码路径，也完成了真实环境验收，但当前不建议直接切为默认中文 ASR。
- 已完成一条真实 B 站链接的端到端验收，验证通过下载、音频标准化、中文转写、`notes.md` 和 `titles.md` 生成链路。
- `retry` 命令现在会按平台识别转写稿文件，B 站任务会检查 `transcript.zh.md`，不再误判为缺少英文稿。

### 5.2 FunASR 真实验收结论

已新增独立记录文档：

```text
docs/funasr-validation.md
```

当前结论：

- `FunASR` 运行环境已经在当前 macOS 机器上安装成功。
- 真实运行中发现并修复了一个 adapter 问题：传入 `Path` 会触发运行时错误，现已改为传字符串路径。
- `FunASR` 模型冷启动较重，真实测试中出现了约 `857MB` 到 `944MB` 级别的模型缓存/下载体量。
- 对 17 分钟左右的 B 站音频，真实推理等待时间仍然偏长，不适合作为当前 MVP 的默认中文 ASR。
- 因此，当前建议保留 `FunASR` 为实验性 Provider，后续再单独优化。

### 6. LLM Provider 与 Prompt 模板

已实现 OpenAI-compatible LLM Provider。

支持通过 `.env` 配置：

```bash
VIDEO2POST_LLM_API_KEY=
VIDEO2POST_LLM_BASE_URL=
VIDEO2POST_LLM_MODEL=
```

当前默认 LLM 稳定性配置：

```text
request_timeout_seconds=300
retry_attempts=2
```

这样在生成 `article.md`、`script.md` 这类更长产物时，对偶发超时和瞬时连接中断更稳一些。

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
- 可选生成 X 向正文和封面图。
- 输出任务目录路径、平台和阶段产物路径。

### 7.1 X 向正文与封面图产物

当前已新增 X 平台优先产物：

- `x_article.md`
- `x_thread.md`
- `x_titles.md`
- `cover.jpg`
- `cover.meta.json`

当前能力：

- 可以基于已有转写稿生成适合 X 平台直接复制发布的长文和 thread。
- 可以生成适合 X 发布场景的标题与开头钩子候选。
- 可以通过 `cover` 目标从视频中按指定时间点截取封面图。
- 可以通过 `cover.meta.json` 回溯封面图来源时间点和源链接。

当前可用命令示例：

```bash
video2post generate TASK_DIR --targets x_article,x_thread,x_titles
video2post generate TASK_DIR --targets cover --cover-at 00:00:30
```

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

当前相关测试通过：

```bash
python3 -m pytest tests/test_pipeline_generate.py tests/test_cli.py -q
# 37 passed
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

## 开发状态总览

### 已完成

- 阶段 0：项目基础骨架
- 阶段 1：任务模型与文件输出
- 阶段 2：YouTube 音频下载与标准化
- 阶段 3：英文 ASR 转写
- 阶段 4：LLM Provider 与 Prompt 模板
- 阶段 5：YouTube 主链路闭环
- 阶段 6：重跑与局部生成
- 阶段 9：固定样例、手工回归基线、真实产物对照文档
- 阶段 10：安装说明、快速开始、`doctor`、常见问题排查

### 部分完成

- 阶段 7：长视频分块处理
  - 已完成基础分块、chunk 摘要、摘要复用
  - 已完成基于 `transcript.segments.json` 的 segment 优先切块，chunk 中会保留时间范围
  - 已完成可选全局摘要层：存在 `global_summary.md` 模板时输出 `summaries/global.summary.md`
  - 仍待补更多真实长视频验收和质量调优

- 阶段 8：B 站中文视频支持
  - 已完成平台识别、音频处理、中文稿输出、`notes/article/script/titles` 生成
  - 已完成真实 B 站样例验收
  - `FunASR` 已接入并做过真实环境测试，但当前不建议作为默认中文 ASR
  - 仍待补更多真实样例交叉验证，以及中文 ASR 默认方案收口

### 已记录但暂缓实现

- 阶段 7.5：`--fast` 快速出稿模式
  - 已讨论并记录方向
  - 暂未进入正式开发

### 新增主线方向

- 优先服务 X 平台发布场景
  - 目标产物会逐步从通用 `article/script/titles`，转向更适合直接发布的 `x_article/x_thread/x_titles`
  - 同时计划补充视频截图封面图产物，例如 `cover.jpg`

### 尚未开始的后续版本方向

- Web 工作台
- 桌面应用
- 本地素材库和检索
- 批量任务队列
- 自动发布到公众号、微博、小红书、B 站等平台
- 本地音频/视频文件输入兜底方案

## 当前限制

目前仍然没有完成：

- Web 工作台。
- 桌面应用。
- 批量任务队列。
- 自动发布到公众号、微博、小红书、B 站等平台。
- 素材库和检索。

长视频和 B 站链路并不是“完全没做”，而是还没有收口到稳定完成态：

- 长视频分块已具备 segment 优先能力：当转写稿长度超过 `generation.chunk_max_chars` 时，系统会优先基于 `transcript.segments.json` 聚合切块，并输出带时间范围的 `chunks/`；随后生成局部摘要到 `summaries/`，如存在 `global_summary.md` 模板，还会生成 `summaries/global.summary.md` 供最终二创内容使用。重新生成最终稿件时，已有且非空的 chunk 摘要和全局摘要会被复用，避免重复调用 LLM。
- B 站中文链路已经能真实跑通，但仍需要继续补真实样例和中文 ASR 默认方案验证。

当前仍需继续完善：

- 更完整的真实长视频测试。
- 继续优化 chunk 边界质量和全局摘要提示词。
- `--fast` 模式和更激进的“快速出稿”链路优化。
- B 站更多真实样例验收和 `FunASR` 独立演进。

## 下一步建议

继续用真实长视频验收阶段 7，并准备推进阶段 7.5：快速出稿模式。

建议顺序：

1. 用一条 30 分钟以上 YouTube 技术视频跑真实验收。
2. 检查 `chunks/` 是否按时间范围合理切分。
3. 检查 `summaries/global.summary.md` 是否覆盖全片主线。
4. 根据真实输出微调 `chunk_summary.md` 和 `global_summary.md`。
5. 进入 `--fast` 快速出稿模式设计与实现。

这样可以让 30-90 分钟技术视频更稳定，也更适合后续真实自媒体工作流。
