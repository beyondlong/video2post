# video2post 需求文档

## 1. 项目背景

`video2post` 是一个面向个人技术博主的本地内容生产工具。项目目标是将高质量视频内容，尤其是 YouTube 英文技术视频和 B 站中文技术视频，转化为可编辑、可二次创作、可发布的中文内容素材。

当前阶段不急于做完整产品，而是先沉淀一个可快速验证的 MVP：通过命令行处理单个视频链接，生成转写稿、中文整理稿，以及适合 X 平台发布的长文、thread 素材、封面图和标题候选，帮助创作者更高效地完成二次创作。

开发阶段拆解见 [开发计划](development-plan.md)。

## 2. 项目目标

### 2.1 核心目标

- 支持粘贴 YouTube 和 B 站视频链接。
- 自动提取视频音频并转成文字。
- 将 YouTube 英文技术视频内容转为中文素材。
- 将 B 站中文技术视频内容整理成结构化文字素材。
- 基于转写内容优先生成可用于 X 平台发布的中文二创内容。
- 支持生成适合作为 X 长文封面的截图图片。
- 所有中间结果和最终结果都以文件形式保存，方便人工校对、复用和长期维护。

### 2.2 MVP 目标

第一版优先做成命令行工具，而不是 Web 或桌面应用。原因是：

- 命令行版本开发速度最快。
- 适合个人技术博主自用和快速试错。
- 可以先验证真实内容生产流程。
- 后续 Web 工作台和桌面应用可以复用同一套核心处理 pipeline。

### 2.3 非目标

第一版暂不做以下内容：

- 抖音、视频号等平台支持。
- 多用户系统。
- 登录、权限、计费。
- Web UI。
- 桌面客户端。
- 批量任务队列。
- 自动发布到公众号、微博、小红书、B 站等平台。
- 视频剪辑、自动配图、自动配音。
- 向量检索或长期素材库。

## 3. 目标用户

第一阶段目标用户是项目作者本人，典型身份是技术博主、开发者、自媒体创作者。

典型使用场景：

- 看到一个高质量 YouTube 英文技术视频，希望转成中文文章或中文讲解稿。
- 看到一个高质量 B 站技术视频，希望快速提取观点和结构。
- 想把视频内容沉淀为可直接发布到 X 的长文、thread 素材、封面图和选题素材。
- 希望保留逐字稿和中间文件，方便后续人工修订和再加工。

## 4. 支持平台范围

### 4.1 第一版支持

- YouTube
- Bilibili

### 4.2 后续可考虑

- TikTok / 抖音
- 视频号
- 小红书视频
- 本地视频或音频文件上传

### 4.3 平台风险

视频平台页面和下载策略会经常变化，尤其是国内平台和短视频平台。第一版依赖 `yt-dlp` 获取音频，但需要接受以下现实：

- 某些链接可能下载失败。
- 某些平台可能需要 Cookie。
- B 站部分内容可能受权限、清晰度、登录状态影响。
- 后续应提供本地音频/视频文件输入作为兜底。

## 5. 第一版产品形态

第一版是一个本地 CLI 工具，暂定命令名：

```bash
video2post
```

典型使用方式：

```bash
video2post "https://www.youtube.com/watch?v=xxxx"
video2post "https://www.bilibili.com/video/BVxxxx"
```

可选参数示例：

```bash
video2post URL --platform youtube
video2post URL --platform bilibili
video2post URL --lang en
video2post URL --lang zh
video2post URL --targets article,script,titles
video2post URL --output ./outputs
```

## 6. 核心处理流程

整体 pipeline：

```text
视频链接
  -> 平台识别
  -> 视频元数据提取
  -> 音频下载
  -> 音频格式标准化
  -> 语音转文字
  -> 文本清洗和分段
  -> 中文翻译或中文整理
  -> 二创内容生成
  -> Markdown 文件输出
```

### 6.1 YouTube 英文视频流程

```text
YouTube 链接
  -> 下载音频
  -> 英文 ASR 转写
  -> 英文逐字稿
  -> 中文翻译和整理
  -> X 长文成稿
  -> X thread 素材
  -> X 标题候选
  -> 封面图
```

### 6.2 B 站中文视频流程

```text
B 站链接
  -> 下载音频
  -> 中文 ASR 转写
  -> 中文逐字稿
  -> 内容清洗和结构化
  -> X 长文成稿
  -> X thread 素材
  -> X 标题候选
  -> 封面图
```

## 7. 输出文件设计

每次处理一个视频，生成一个独立输出目录。

目录结构示例：

```text
outputs/
  2026-04-29-video-title/
    meta.json
    audio.wav
    transcript.en.md
    transcript.zh.md
    notes.md
    x_article.md
    x_thread.md
    x_titles.md
    cover.jpg
    cover.meta.json
    article.md
    script.md
    titles.md
```

### 7.1 `meta.json`

保存任务元数据：

- 原始链接
- 平台
- 视频标题
- 作者
- 视频时长
- 发布时间
- 下载时间
- 使用的 ASR 模型
- 使用的大模型
- 处理状态
- 错误信息

### 7.2 `audio.wav`

标准化后的音频文件。

建议格式：

- WAV
- 16kHz
- mono

### 7.3 `transcript.en.md`

YouTube 英文视频的英文逐字稿。

内容应尽量保留原始表达，方便回查。

### 7.4 `transcript.zh.md`

中文整理稿。

对于 YouTube 视频，它是英文逐字稿的中文翻译和整理版。  
对于 B 站视频，它是中文逐字稿的清洗和分段版。

### 7.5 `notes.md`

内容笔记。

建议包含：

- 核心观点
- 技术概念
- 重要案例
- 可引用金句
- 术语解释
- 适合二创的角度

### 7.6 `article.md`

技术博客或公众号长文草稿。

要求：

- 结构完整。
- 适合中文读者阅读。
- 不简单逐句翻译。
- 能保留原视频的核心价值。
- 可加入适度解释，但不能虚构原视频不存在的事实。

### 7.6.1 `x_article.md`

优先面向 X 平台长文发布的正文草稿。

要求：

- 开头直接给结论、亮点或争议点。
- 段落较短，适合 X 阅读节奏。
- 可以直接复制后做少量人工调整再发布。

### 7.6.2 `x_thread.md`

适合拆成 X thread 的短段版本。

要求：

- 每段相对独立但整体连贯。
- 优先突出观点推进和传播性。

### 7.6.3 `x_titles.md`

适合 X 发布场景的标题、开头钩子或首帖候选。

### 7.6.4 `cover.jpg`

从视频中抽取并适配的封面图片，优先用于 X 长文封面。

### 7.6.5 `cover.meta.json`

记录封面图来源信息，例如截图时间点、裁剪策略、原始视频链接和是否叠加文案。

### 7.7 `script.md`

短视频口播稿。

要求：

- 更口语化。
- 开头有明确钩子。
- 适合 1-3 分钟中文讲解。
- 结构清晰。
- 适合后续录制视频号、B 站、抖音等平台内容。

### 7.8 `titles.md`

标题候选。

建议包含：

- 技术博客标题
- 公众号标题
- 短视频标题
- 更理性/专业的标题
- 更有传播感的标题

## 8. 技术选型

### 8.0 总体技术方向

项目采用 CLI-first 的技术路线：第一版先做本地命令行工具，快速跑通真实内容生产流程；后续再演进为 Web 工作台和桌面应用。

总体原则：

- 核心能力优先沉淀为可复用的 Python pipeline。
- CLI、Web、桌面应用都只作为入口层。
- 下载、音频处理、转写、LLM 生成、文件输出等能力不绑定具体 UI。
- 第一版优先保证稳定转写和 Markdown 产物质量，不急于做复杂交互。

推荐演进顺序：

```text
CLI MVP
  -> 个人 Web 工作台
  -> 桌面应用
  -> 素材库和检索系统
```

### 8.1 开发语言

推荐使用 Python。

原因：

- ASR、音频处理、AI 工具生态成熟。
- `yt-dlp`、`faster-whisper`、`FunASR` 等核心工具都适合 Python 集成。
- CLI 和后续服务化都方便。
- 项目的核心是媒体处理和 AI pipeline，而不是高并发 Web 服务。
- 后续如果使用 FastAPI 做 Web 后端，可以直接复用同一套核心逻辑。

不优先选择其他语言的原因：

- Node.js 更适合前端和 Web 层，但 ASR、音频、模型生态最终仍会依赖 Python。
- Go 适合分发和并发，但 AI 工具生态不如 Python 直接。
- Java 工程化能力强，但用于个人 AI 内容工具会偏重。
- Rust 性能好，但第一版开发效率和 AI 生态集成成本较高。

结论：

- 主语言：Python
- 前端预留：React / Vite
- Web 后端预留：FastAPI
- 桌面端预留：Tauri

### 8.1.1 运行环境

第一版优先支持 macOS，后续再考虑 Linux 和 Windows。

macOS 优先的原因：

- 项目作者当前开发和使用环境优先面向 macOS。
- Homebrew 安装 `ffmpeg` 等系统依赖较方便。
- 先减少跨平台适配成本，把主要精力放在内容生产 pipeline 上。

第一版建议环境：

- macOS
- Python 3.11+
- ffmpeg
- yt-dlp
- faster-whisper
- FunASR
- 云端大模型 API Key

后续跨平台支持策略：

- Linux 作为第二优先级。
- Windows 暂不作为第一版目标，可在 CLI MVP 稳定后再评估。
- 尽量避免在核心 pipeline 中写死 macOS 专有路径。
- 系统依赖安装说明应独立维护，便于后续增加 Linux/Windows 章节。

### 8.2 CLI 框架

推荐：

- `typer`

原因：

- 类型提示友好。
- 参数定义清晰。
- 后续扩展子命令方便。

第一版 CLI 是项目主要入口。CLI 层只负责解析参数、读取配置、调用 pipeline，不承载复杂业务逻辑。

建议命令形态：

```bash
video2post URL
video2post URL --platform youtube
video2post URL --platform bilibili
video2post URL --lang en
video2post URL --lang zh
video2post URL --targets article,script,titles
video2post URL --output ./outputs
```

后续可扩展子命令：

```bash
video2post transcribe URL
video2post generate ./outputs/task-dir
video2post retry ./outputs/task-dir
video2post config show
```

### 8.3 视频下载

推荐：

- `yt-dlp`

用途：

- 解析 YouTube/B 站链接。
- 获取视频元数据。
- 下载音频。

### 8.4 音频处理

推荐：

- `ffmpeg`

用途：

- 抽取音频。
- 转换格式。
- 采样率统一。
- 后续可做切片、去静音等处理。

### 8.5 英文 ASR

推荐：

- `faster-whisper`

用途：

- YouTube 英文技术视频转写。

优势：

- 基于 Whisper。
- 推理速度较快。
- 适合本地运行。

### 8.6 中文 ASR

推荐：

- `FunASR`

用途：

- B 站中文技术视频转写。

优势：

- 中文识别能力较好。
- 支持 VAD、标点恢复等能力。
- 更适合中文视频场景。

第一版实施建议：

- 可以先预留统一 ASR 接口。
- 优先跑通 `faster-whisper + YouTube`。
- 再接入 `FunASR + B 站`。
- 不要求一开始就把所有 ASR 能力做完整。

统一 ASR 接口应屏蔽不同模型差异，向 pipeline 输出统一结构，例如：

```text
segments:
  - start
  - end
  - text
  - language
```

### 8.7 云端大模型

第一版采用本地运行工具 + 云端大模型 API 的方式。

用途：

- 英文转中文。
- 内容总结。
- 结构化整理。
- 长文生成。
- 短视频口播稿生成。
- 标题生成。

后续可扩展支持：

- OpenAI
- 通义千问
- DeepSeek
- Claude
- Gemini
- Ollama 本地模型

第一版优先使用云端大模型，而不是本地大模型。

原因：

- 二创生成质量更稳定。
- 中文长文、口播稿、标题生成效果更好。
- 本地硬件压力更小。
- 可以把主要开发精力放在 pipeline 和产物质量上。

LLM 层需要抽象为独立模块，避免绑定单一供应商。建议统一封装：

- `generate_translation`
- `generate_notes`
- `generate_article`
- `generate_script`
- `generate_titles`

提示词应强调：

- 不虚构事实。
- 不添加原视频没有的数据。
- 不直接搬运原文表达。
- 保持适合中文技术读者的表达。
- 明确区分“原视频观点”和“整理者补充说明”。

### 8.7.1 LLM Provider 抽象

LLM 调用需要在第一版就做成可替换 Provider，而不是把某个供应商 API 写死在业务流程中。

第一版推荐优先支持 OpenAI-compatible API。

原因：

- 很多云端模型服务都兼容 OpenAI 风格接口。
- 后续可以较低成本接入 OpenAI、通义千问、DeepSeek、硅基流动等服务。
- 也方便将来接入本地 Ollama 或其他自部署模型。

建议抽象能力：

```text
LLMProvider
  - generate(prompt, context, options)
  - generate_translation(transcript)
  - generate_notes(transcript)
  - generate_article(notes, transcript)
  - generate_script(notes, transcript)
  - generate_titles(notes, article)
```

建议配置项：

```yaml
llm:
  provider: openai_compatible
  base_url: https://api.example.com/v1
  model: example-model
  temperature: 0.7
  max_tokens: 4096
```

API Key 不应写入 `config.yaml`，应通过 `.env` 或系统环境变量提供。

### 8.7.2 Prompt 模板管理

二创生成提示词需要独立管理，避免散落在代码中。

建议目录：

```text
prompts/
  translation.md
  notes.md
  article.md
  script.md
  titles.md
```

Prompt 模板应支持变量注入，例如：

```text
{{ video_title }}
{{ video_author }}
{{ platform }}
{{ transcript }}
{{ notes }}
{{ target_style }}
```

这样后续可以在不改代码的情况下持续调整内容风格。

第一版重点维护的模板：

- `translation.md`：英文逐字稿转中文整理稿。
- `notes.md`：提取核心观点、术语、案例、金句和二创角度。
- `article.md`：生成中文技术长文或公众号草稿。
- `script.md`：生成 1-3 分钟短视频口播稿。
- `titles.md`：生成多种发布场景的标题候选。

Prompt 模板原则：

- 明确要求基于原视频内容。
- 明确禁止虚构事实。
- 明确输出结构。
- 区分“原视频内容”和“整理者补充说明”。
- 优先服务中文技术读者。

### 8.8 配置管理

建议使用：

- `.env`
- `config.yaml`

配置内容包括：

- 大模型 API Key
- 默认模型
- 默认输出目录
- 默认 ASR 模型
- 是否保留音频文件
- 是否跳过已存在步骤

### 8.9 项目结构建议

第一版虽然是 CLI，但应按后续可扩展的方式组织代码。

建议结构：

```text
video2post/
  cli.py
  config.py
  pipeline.py
  models.py
  downloader/
    base.py
    ytdlp.py
  audio/
    ffmpeg.py
  asr/
    base.py
    faster_whisper.py
    funasr.py
  llm/
    base.py
    providers/
    prompts/
  writers/
    markdown.py
    metadata.py
  utils/
docs/
outputs/
```

分层说明：

- CLI 层：解析命令参数。
- Pipeline 层：编排完整任务。
- Downloader 层：处理链接、元数据和音频下载。
- Audio 层：处理音频标准化。
- ASR 层：语音转文字。
- LLM 层：翻译、总结和二创生成。
- Writer 层：输出 Markdown 和元数据文件。

### 8.10 Web 版本技术方向

CLI MVP 跑通后，第二阶段可以做个人 Web 工作台。

推荐技术栈：

- FastAPI
- SQLite
- React / Vite

Web 版定位：

- 粘贴链接。
- 查看任务进度。
- 在线查看逐字稿。
- 重新生成文章、口播稿、标题。
- 管理历史任务。

Web 后端不应重新实现业务逻辑，而是调用已有 Python pipeline。

### 8.11 桌面版本技术方向

第三阶段可以考虑桌面应用。

推荐技术栈：

- Tauri
- React
- Python sidecar

桌面版定位：

- 更适合个人日常使用。
- 简化本地启动体验。
- 提供更完整的素材管理和编辑体验。

桌面版不建议作为第一版，原因是：

- 打包 Python、ffmpeg、ASR 模型会增加复杂度。
- 跨平台兼容成本较高。
- 在未验证内容工作流前，过早做桌面 UI 容易浪费时间。

### 8.12 数据存储策略

第一版使用文件系统作为主要存储。

原因：

- 简单直接。
- 方便人工查看和修改。
- 方便 Git 管理和备份。
- 适合 Markdown 内容生产。

第二阶段 Web 工作台可引入 SQLite。

SQLite 主要保存：

- 任务列表。
- 视频元数据。
- 处理状态。
- 输出文件路径。
- 生成历史。

正文内容仍建议保留为 Markdown 文件，而不是完全存入数据库。

## 9. 关键能力要求

### 9.1 可重跑

处理过程应分阶段落盘，避免失败后从头开始。

例如：

- 如果已存在 `audio.wav`，可以跳过下载。
- 如果已存在 `transcript.en.md`，可以跳过转写。
- 如果只想重新生成 `article.md`，不需要重新下载和转写。

建议为每个任务维护明确状态，状态写入 `meta.json`。

任务状态示例：

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

每个阶段完成后立即落盘。失败时应记录：

- 当前阶段。
- 错误类型。
- 错误信息。
- 是否可以重试。

CLI 后续可以提供重跑能力：

```bash
video2post retry ./outputs/task-dir
video2post generate ./outputs/task-dir --targets article,titles
```

这能避免长视频处理失败后从头下载或重新转写。

### 9.2 可人工校对

所有输出都应是可编辑文本文件，优先使用 Markdown。

原因：

- 方便人工修订。
- 方便复制到公众号、博客、知识库。
- 方便版本管理。

### 9.3 可扩展

虽然第一版是 CLI，但核心处理逻辑应独立于 CLI。

建议分层：

- CLI 层：解析命令参数。
- Pipeline 层：编排任务流程。
- Downloader 层：下载和元数据。
- Audio 层：音频处理。
- ASR 层：语音转文字。
- LLM 层：二创生成。
- Writer 层：输出文件。

这样后续做 Web UI 或桌面应用时，可以直接复用 Pipeline。

### 9.4 长视频处理

YouTube 技术视频经常达到 30-90 分钟，第一版需要提前考虑长视频处理策略。

长视频主要风险：

- 音频文件较大，下载和转码时间长。
- ASR 推理耗时较长。
- 逐字稿过长，可能超过大模型上下文限制。
- 一次性生成文章容易丢失细节或结构混乱。

建议策略：

- ASR 阶段按时间 segment 输出，不只保存整段文本。
- LLM 阶段采用分块处理。
- 先对每个分块生成局部摘要。
- 再基于局部摘要生成全局笔记。
- 最后基于全局笔记和必要原文片段生成文章、口播稿和标题。

分块策略示例：

```text
transcript segments
  -> chunk 1 summary
  -> chunk 2 summary
  -> chunk 3 summary
  -> global notes
  -> article / script / titles
```

第一版可采用简单规则：

- 按 ASR segment 累积文本长度切块。
- 每块控制在大模型可处理上下文范围内。
- 保留 chunk 序号和时间范围，方便回查。

建议输出中间文件：

```text
chunks/
  chunk-001.md
  chunk-002.md
  chunk-003.md
summaries/
  chunk-001.summary.md
  chunk-002.summary.md
  chunk-003.summary.md
```

这样既能支持长视频，也方便人工检查中间结果。

## 10. 第一版开发边界与验收

### 10.1 MVP 验收标准

第一版 MVP 完成的标准不是功能完整，而是能稳定跑通一个真实内容生产闭环。

最低验收标准：

- 能通过命令行处理一个 YouTube 英文技术视频链接。
- 能生成标准化音频文件。
- 能生成英文逐字稿 `transcript.en.md`。
- 能生成中文整理稿 `transcript.zh.md`。
- 能生成内容笔记 `notes.md`。
- 能生成技术长文草稿 `article.md`。
- 能生成短视频口播稿 `script.md`。
- 能生成标题候选 `titles.md`。
- 能将任务元数据和状态写入 `meta.json`。
- 失败时能记录失败阶段和错误信息。
- 已完成的阶段可以跳过，避免重跑全部流程。

扩展验收标准：

- 能处理一个 B 站中文技术视频链接。
- 能使用中文 ASR 生成中文逐字稿。
- 能基于中文逐字稿生成笔记、长文、口播稿和标题。
- 能通过 `generate` 命令重新生成部分二创产物。
- 能通过 `retry` 命令从失败任务继续处理。

### 10.2 第一版最小命令集

第一版只实现必要命令，避免 CLI 过早复杂化。

必须实现：

```bash
video2post URL
```

用途：

- 自动识别平台。
- 下载音频。
- 执行转写。
- 执行 LLM 生成。
- 输出完整任务目录。

建议实现：

```bash
video2post retry TASK_DIR
```

用途：

- 从已有任务目录读取 `meta.json`。
- 根据任务状态继续未完成阶段。

```bash
video2post generate TASK_DIR --targets article,script,titles
```

用途：

- 基于已有逐字稿和笔记重新生成指定二创内容。
- 不重新下载音频。
- 不重新执行 ASR。

```bash
video2post config show
```

用途：

- 查看当前生效配置。
- 帮助排查 API、模型和输出目录问题。

暂缓实现：

- 批量处理命令。
- 自动发布命令。
- 任务列表命令。
- Web 服务启动命令。

### 10.3 配置文件规范

项目应提供 `.env.example` 和 `config.example.yaml`，降低本地启动成本。

`.env.example` 示例：

```bash
VIDEO2POST_LLM_API_KEY=
VIDEO2POST_LLM_BASE_URL=
VIDEO2POST_LLM_MODEL=
```

`config.example.yaml` 示例：

```yaml
app:
  output_dir: outputs
  keep_audio: true
  skip_existing: true

download:
  preferred_audio_format: wav
  cookies_file:
  cookies_from_browser:

audio:
  sample_rate: 16000
  channels: 1

asr:
  default_language: auto
  english_provider: faster_whisper
  chinese_provider: funasr
  faster_whisper_model: medium
  funasr_model: paraformer

llm:
  provider: openai_compatible
  base_url:
  model:
  temperature: 0.7
  max_tokens: 4096

generation:
  default_targets:
    - translation
    - notes
    - article
    - script
    - titles
  chunk_max_chars: 6000
```

配置原则：

- API Key 只放 `.env` 或系统环境变量。
- `config.yaml` 不提交真实密钥。
- 示例配置可以提交到仓库。
- CLI 参数优先级高于配置文件。
- 配置文件优先级高于默认值。

### 10.4 输出 Markdown 模板规范

第一版输出文件应采用稳定、可读、可人工编辑的 Markdown 结构。

通用要求：

- 文件开头包含视频标题、平台、原始链接和生成时间。
- 对于转写内容，尽量保留时间戳。
- 对于二创内容，明确区分正文、摘要、标题和备注。
- 不在 Markdown 中写入 API Key 或敏感配置。

`transcript.en.md` 示例结构：

```markdown
# Transcript EN: {{ video_title }}

- Platform: {{ platform }}
- Source: {{ source_url }}
- Generated At: {{ generated_at }}

## Segments

### [00:00:00 - 00:00:15]

Original English text...
```

`transcript.zh.md` 示例结构：

```markdown
# 中文整理稿：{{ video_title }}

- 平台：{{ platform }}
- 来源：{{ source_url }}
- 生成时间：{{ generated_at }}

## 分段整理

### [00:00:00 - 00:00:15]

中文翻译或中文清洗内容...
```

`notes.md` 示例结构：

```markdown
# 内容笔记：{{ video_title }}

## 核心观点

## 技术概念

## 重要案例

## 可引用金句

## 术语解释

## 二创角度
```

`article.md` 示例结构：

```markdown
# {{ article_title }}

## 摘要

## 正文

## 来源与备注
```

`script.md` 示例结构：

```markdown
# 短视频口播稿：{{ video_title }}

## 开场钩子

## 正文脚本

## 结尾引导
```

`titles.md` 示例结构：

```markdown
# 标题候选：{{ video_title }}

## 技术博客标题

## 公众号标题

## 短视频标题

## 理性专业风格

## 传播感风格
```

### 10.5 测试样例策略

第一版开发时应准备少量稳定样例，作为手工验收和回归检查依据。

建议样例：

- 一个 5-10 分钟的 YouTube 英文技术视频。
- 一个 5-10 分钟的 B 站中文技术视频。
- 一个无效或无法访问的视频链接。
- 一个较长的 YouTube 英文技术视频，用于验证分块策略。

每个样例应记录：

- 原始链接。
- 平台。
- 预期语言。
- 是否需要 Cookie。
- 预期输出文件。
- 已知风险或备注。

测试重点：

- 链接解析是否正确。
- 音频下载是否成功。
- 音频标准化是否成功。
- ASR 是否生成可读文本。
- LLM 是否生成所有目标文件。
- 失败时 `meta.json` 是否记录错误。
- 重跑时是否跳过已完成阶段。

自动化测试可以后续补充，第一版至少要保留固定样例和手工验收步骤。

## 11. 后续演进路线

### 11.1 阶段一：CLI MVP

目标：

- 单链接处理。
- YouTube/B 站支持。
- 本地 ASR。
- 云端大模型生成二创内容。
- Markdown 输出。

### 11.2 阶段二：个人 Web 工作台

目标：

- Web 页面粘贴链接。
- 查看任务进度。
- 在线查看和编辑逐字稿。
- 一键重新生成长文、口播稿和标题。
- 保存历史任务。

可能技术栈：

- FastAPI
- SQLite
- React 或 Next.js

### 11.3 阶段三：桌面应用

目标：

- 更适合个人日常使用。
- 简化本地依赖安装。
- 提供更完整的素材管理体验。

可能技术栈：

- Tauri
- Electron
- Python sidecar

### 11.4 阶段四：素材库和检索

目标：

- 保存长期处理过的视频内容。
- 支持按主题、作者、关键词检索。
- 支持向量搜索。
- 支持同主题视频对比总结。

## 12. 风险与注意事项

### 12.1 版权和合规

项目用于个人学习、整理和二次创作辅助。生成内容时应避免直接搬运原视频表达。

二创内容应：

- 尊重原作者。
- 保留事实准确性。
- 避免大段照搬。
- 必要时标注来源。

### 12.2 平台可用性

`yt-dlp` 支持大量平台，但平台规则变化可能导致下载失败。项目需要把下载失败视为常见情况，而不是异常边缘情况。

### 12.3 转写准确率

ASR 转写可能受以下因素影响：

- 视频音质。
- 背景音乐。
- 说话人语速。
- 技术术语。
- 中英文混杂。
- 口音。

因此第一版必须保留逐字稿，允许人工校对。

### 12.4 大模型幻觉

大模型在总结和二创时可能会补充原视频没有的信息。提示词需要明确要求：

- 不虚构事实。
- 不添加原视频未提到的数据。
- 不夸大结论。
- 对不确定内容保持谨慎。

## 13. 待确认问题

后续进入实现前，需要继续确认：

- 第一版使用哪个云端大模型 API。
- 是否需要 Docker 化。
- 是否保留原始下载文件。
- YouTube 英文视频是否需要同时保留英文原稿和中文翻译。
- B 站视频是否需要支持登录 Cookie。
- 长文和口播稿的默认风格模板。
- 是否需要输出适配微信公众号格式的 HTML。
