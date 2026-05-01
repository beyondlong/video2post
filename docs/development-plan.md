# video2post 开发计划

> 本计划基于 `docs/requirements.md`，用于指导第一阶段 CLI MVP 的实现顺序。目标是先跑通主链路，再逐步补齐可靠性、可维护性和后续扩展能力。

## 总体原则

- 先完成 YouTube 英文视频到适合 X 平台发布的中文内容主流程。
- 再补 B 站中文视频支持。
- 所有阶段都要能落盘，避免失败后从头开始。
- 第一版优先服务个人自用，不做复杂平台化能力。
- CLI、Web、桌面应用共享同一套核心 pipeline，避免后续重写。

## 阶段 0：项目基础骨架

目标：建立可开发、可运行、可测试的 Python CLI 项目基础。

主要任务：

- 初始化 Python 项目结构。
- 确定包管理方式。
- 创建 CLI 入口 `video2post`。
- 创建基础模块目录。
- 添加基础配置文件。
- 添加 `.env.example`。
- 添加 `config.example.yaml`。
- 添加基础测试目录。
- 配置代码格式化和测试命令。

建议产物：

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
  utils/
tests/
.env.example
config.example.yaml
```

验收标准：

- 可以运行 `video2post --help`。
- 可以读取默认配置。
- 可以运行基础测试。

## 阶段 1：任务模型与文件输出

目标：先把任务目录、元数据、状态机和 Markdown 输出结构做稳。

主要任务：

- 定义任务状态枚举。
- 定义任务元数据模型。
- 实现任务目录创建。
- 实现 `meta.json` 读写。
- 实现 Markdown 文件写入工具。
- 实现输出文件模板结构。
- 支持阶段状态更新。
- 支持失败信息记录。

优先状态：

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

验收标准：

- 给定一个模拟视频元数据，可以创建完整任务目录。
- 可以写入和更新 `meta.json`。
- 可以生成空的或模拟内容的 Markdown 产物。
- 失败时可以记录失败阶段和错误信息。

## 阶段 2：YouTube 音频下载与标准化

目标：完成从 YouTube 链接到标准音频文件的流程。

主要任务：

- 使用 `yt-dlp` 获取 YouTube 视频元数据。
- 下载音频文件。
- 使用 `ffmpeg` 转换为标准格式。
- 输出 `audio.wav`。
- 更新任务状态。
- 支持跳过已存在音频。

建议音频格式：

```text
WAV
16kHz
mono
```

验收标准：

- 输入一个 YouTube 视频链接，可以生成 `audio.wav`。
- `meta.json` 包含视频标题、作者、平台、原始链接等信息。
- 重复执行时可以跳过已完成下载和转码步骤。

## 阶段 3：英文 ASR 转写

目标：接入 `faster-whisper`，完成 YouTube 英文视频转写。

主要任务：

- 定义统一 ASR 接口。
- 实现 `faster-whisper` Provider。
- 输出统一 segment 结构。
- 生成 `transcript.en.md`。
- 保留时间戳。
- 支持跳过已存在转写文件。

统一 segment 结构：

```text
start
end
text
language
```

验收标准：

- 输入 `audio.wav` 可以生成英文逐字稿。
- `transcript.en.md` 内容可读，并包含时间戳。
- 转写完成后任务状态更新为 `transcribed`。

## 阶段 4：LLM Provider 与 Prompt 模板

目标：建立可替换的大模型调用层和独立 Prompt 模板管理。

主要任务：

- 定义 LLM Provider 接口。
- 优先实现 OpenAI-compatible Provider。
- 从 `.env` 读取 API Key。
- 从 `config.yaml` 读取 base URL、模型和生成参数。
- 创建 Prompt 模板目录。
- 实现变量注入。
- 实现基础生成方法。

Prompt 模板：

```text
prompts/
  translation.md
  notes.md
  article.md
  script.md
  titles.md
```

验收标准：

- 可以通过配置切换 OpenAI-compatible 模型。
- API Key 不写入仓库配置。
- 可以使用模板和输入文本生成一段测试内容。

## 阶段 5：YouTube 主链路闭环

目标：跑通第一版最核心能力：YouTube 英文视频到适合 X 平台发布的中文内容素材。

主要任务：

- 基于 `transcript.en.md` 生成 `transcript.zh.md`。
- 生成 `notes.md`。
- 生成 `x_article.md`。
- 生成 `x_thread.md`。
- 生成 `x_titles.md`。
- 预留传统 `article.md`、`script.md`、`titles.md` 作为兼容产物。
- 完成 pipeline 编排。
- 实现 `video2post URL` 主命令。

验收标准：

- 输入一个 YouTube 英文技术视频链接后，可以输出完整任务目录。
- 至少生成以下文件：

```text
meta.json
audio.wav
transcript.en.md
transcript.zh.md
notes.md
x_article.md
x_thread.md
x_titles.md
```

- 失败时能写入 `meta.json`。
- 重复执行时能跳过已完成步骤。

这是第一版 MVP 的主验收点。

## 阶段 6：重跑与局部生成

目标：让工具适合真实使用，避免每次都从头跑。

主要任务：

- 实现 `video2post retry TASK_DIR`。
- 实现 `video2post generate TASK_DIR --targets article,script,titles`。
- 支持基于已有转写和笔记重新生成二创内容。
- 支持只重新生成指定目标文件。
- 支持查看当前配置 `video2post config show`。

验收标准：

- 删除 `article.md` 后，可以只重新生成文章。
- LLM 失败后，可以从失败阶段继续。
- 不需要重新下载音频或重新 ASR。

## 阶段 7：长视频分块处理

目标：让 30-90 分钟技术视频也能稳定处理。

当前状态：已开始实现基础分块链路。超过 `generation.chunk_max_chars` 的转写稿会输出 `chunks/` 和 `summaries/`，最终生成阶段会使用 chunk 摘要代替完整转写稿。

主要任务：

- 按 ASR segment 累积文本切块。
- 输出 `chunks/chunk-001.md` 等中间文件。
- 对每个 chunk 生成局部摘要。
- 输出 `summaries/chunk-001.summary.md` 等中间文件。
- 基于局部摘要生成全局笔记。
- 再生成长文、口播稿和标题。

验收标准：

- 较长 YouTube 视频不会因为上下文过长直接失败。
- 中间 chunk 和 summary 文件可检查。
- 最终文章结构完整，不明显丢失主线。

## 阶段 7.5：快速出稿模式

目标：在不牺牲基本可用性的前提下，优先缩短“音频 -> 英文稿 -> 中文整理稿”的等待时间。

当前状态：已讨论并记录需求，暂缓实现，后续在阶段 7 完善后继续推进。

主要任务：

- 设计 `--fast` 模式。
- 使用更轻量的 ASR 模型作为默认快速通道。
- 默认输出段落版转写稿，减少不必要的时间戳文本干扰。
- 保留原始 segment 到独立 JSON 文件，兼顾后续精校和切片。
- 优先生成更适合二创的中文整理稿，而不是完整逐字直译稿。
- 评估是否减少默认生成目标，进一步缩短首轮等待时间。

验收标准：

- 同一条 YouTube 视频在快速模式下的首轮可读结果明显更快产出。
- 用户可以快速拿到适合二创的中文素材。
- 如需更精细结果，仍可回退到完整链路。

## 阶段 8：B 站中文视频支持

目标：补齐第二个目标平台，支持中文视频转写和面向 X 的二创产物生成。

当前状态：基础链路已开始实现。平台识别、音频处理、中文转写输出和基于中文稿的生成流程已经接通；`FunASR` Provider 已接入代码路径，也完成了一轮真实环境验收，但当前结论是不适合作为默认中文 ASR，仍保留为实验性方案。

主要任务：

- 识别 B 站链接。
- 使用 `yt-dlp` 获取 B 站视频元数据。
- 下载并标准化音频。
- 定义中文 ASR Provider。
- 接入 `FunASR`。
- 生成中文逐字稿或中文整理稿。
- 复用 notes 和 X 向稿件生成流程。

验收标准：

- 输入一个 B 站中文技术视频链接，可以生成完整任务目录。
- 不依赖英文翻译流程。
- 中文逐字稿可读。
- 能生成笔记、X 长文、X thread、X 标题和兼容稿件。

## 阶段 8.5：X 发布产物增强

目标：让生成结果更贴近“可直接复制到 X 发布”的最终形态。

主要任务：

- 设计 `x_article.md` 的专用 Prompt 和结构。
- 设计 `x_thread.md` 的拆分格式。
- 设计 `x_titles.md` 的开头钩子和标题模板。
- 从视频中抽取封面截图。
- 输出 `cover.jpg` 和 `cover.meta.json`。
- 支持指定截图时间点或自动选择少量候选帧。

验收标准：

- 同一条视频可以产出适合直接发 X 的长文正文。
- 可以产出适合拆帖发布的 thread 版本。
- 可以产出至少一张可用作封面的截图图片。
- 封面图来源时间点和裁剪信息可追溯。

## 阶段 9：测试样例与回归检查

目标：固定少量样例，保证后续修改不破坏主流程。

主要任务：

- 记录一个短 YouTube 英文技术视频样例。
- 记录一个短 B 站中文技术视频样例。
- 记录一个无效链接样例。
- 记录一个长 YouTube 视频样例。
- 编写手工验收步骤。
- 补充核心单元测试。

测试重点：

- 链接解析。
- 任务目录创建。
- `meta.json` 状态更新。
- Markdown 输出。
- 配置加载。
- LLM 模板渲染。
- 阶段跳过和重跑。

验收标准：

- 每次关键修改后，可以用固定样例验证主流程。
- 单元测试覆盖不依赖外部网络的核心逻辑。

## 阶段 10：文档与使用体验打磨

目标：让项目能被自己稳定使用，也方便后续开源维护。

主要任务：

- 补充安装说明。
- 补充 macOS 环境依赖说明。
- 补充 CLI 使用示例。
- 补充配置说明。
- 补充常见错误排查。
- 更新 README。
- 更新需求文档。

验收标准：

- 从空环境开始，能按 README 配置并跑通一个样例。
- 常见失败原因有明确说明。
- 文档和实际命令保持一致。

## 优先级总结

### P0：必须先完成

- 项目骨架。
- 任务目录和状态机。
- YouTube 音频下载。
- 音频标准化。
- `faster-whisper` 英文转写。
- OpenAI-compatible LLM Provider。
- Prompt 模板。
- YouTube 完整主链路。

### P1：第一版体验关键

- 断点续跑。
- 局部重新生成。
- 配置展示。
- 长视频分块。
- X 平台成稿和封面图。
- 固定测试样例。

### P2：第一版扩展目标

- B 站中文视频。
- `FunASR` 中文转写。
- 更完整的错误处理。
- 文档和安装体验打磨。

### P3：后续版本考虑

- 字幕优先。
- Cookie 支持。
- 本地文件输入。
- Web 工作台。
- 桌面应用。
- 素材库和检索。
