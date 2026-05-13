# video2post

`video2post` 是一个面向技术博主和内容创作者的本地内容生产工具。它的目标是把高质量视频内容，尤其是 YouTube 英文技术视频和 B 站中文技术视频，转化为可编辑、可二次创作、可发布的中文内容素材。

项目当前处于早期规划和 MVP 阶段，第一版会优先做成本地 CLI 工具，用最短路径跑通“视频链接 -> 音频 -> 转写 -> 中文整理 -> 适合 X 平台发布的长文与 thread 素材”的完整流程。

当前已完成进度和可测试效果见：[docs/progress.md](docs/progress.md)。固定回归样例见：[docs/samples.md](docs/samples.md)。手工回归检查表见：[docs/manual-checklist.md](docs/manual-checklist.md)。真实验收产物对照见：[docs/test-fixtures.md](docs/test-fixtures.md)。

当前安装与运行说明见：[docs/setup.md](docs/setup.md)。

## 快速开始

如果你只是想尽快在 macOS 上跑通一个样例，按下面 5 步来：

1. 安装系统依赖

```bash
brew install ffmpeg yt-dlp
brew install node
```

2. 安装项目依赖

```bash
python3 -m pip install -e '.[dev]'
python3 -m pip install -e '.[asr]'
```

如果你想在 Apple Silicon 上实验更快的英文本地转写，也可以安装：

```bash
python3 -m pip install -e '.[asr-mlx]'
```

3. 配置 `.env`

```bash
VIDEO2POST_LLM_API_KEY=your-key
VIDEO2POST_LLM_BASE_URL=https://api.minimaxi.com/v1
VIDEO2POST_LLM_MODEL=MiniMax-M2.7
```

如果某些 YouTube 视频提示需要登录或确认不是机器人，建议再创建一个 `config.yaml`：

```yaml
download:
  cookies_from_browser: chrome
  js_runtimes: node
  remote_components: ejs:github
```

如果你的 YouTube 登录态在 Safari，就把 `chrome` 改成 `safari`。

4. 确认 CLI 可用

```bash
python3 -m video2post.cli --help
python3 -m video2post.cli samples
python3 -m video2post.cli doctor
```

5. 跑一个最小样例

```bash
video2post video "https://www.youtube.com/watch?v=474wZZHoWN4" --output ./outputs-check --generate --targets notes,titles --cleanup-source
```

如果你当前 shell 里的 `video2post` 还没指向这个仓库，可以改用：

```bash
python3 -m video2post.cli video "https://www.youtube.com/watch?v=474wZZHoWN4" --output ./outputs-check --generate --targets notes,titles --cleanup-source
```

## 核心目标

- 支持 YouTube 和 B 站视频链接。
- 自动下载或提取视频音频。
- 将 YouTube 英文技术视频转写并整理为中文内容。
- 将 B 站中文技术视频转写并结构化整理。
- 优先生成适合 X 平台发布的长文、thread 素材、标题候选和内容笔记。
- 后续支持从视频截图生成适合作为 X 封面的图片。
- 所有中间结果和最终结果都保存为本地文件，方便人工校对和复用。

## 第一版形态

第一版采用 CLI-first 路线，推荐命令名：

```bash
video2post
```

示例用法：

```bash
video2post video "https://www.youtube.com/watch?v=xxxx"
video2post video "https://www.bilibili.com/video/BVxxxx"
video2post video ./local-video.mp4 --lang zh --fast
video2post video ./local-audio.wav --lang zh --generate
```

如果当前 shell 里的 `video2post` 命令还没有正确绑定到这个仓库，也可以先用：

```bash
python3 -m video2post.cli --help
python3 -m video2post.cli samples
```

可选参数方向：

```bash
video2post video URL --output ./outputs
video2post video URL --fast
video2post video URL --generate --targets x_article,x_thread,x_titles
video2post video URL --lang zh --generate
video2post video URL --generate --targets cover --cover-at 00:00:30
video2post video URL --cleanup-source
video2post video URL --no-transcribe
video2post video URL --lang zh
video2post video URL --no-download
video2post video ./local-video.mp4 --fast
video2post video ./local-audio.wav --lang zh --generate
video2post draft "原始内容" --mode x_engage
video2post draft "原始内容" --mode viral_280
video2post draft --x-url "https://x.com/user/status/123"
```

LLM 相关配置既可以放在 `.env`，也可以放在 `config.yaml`：

```yaml
llm:
  base_url: https://api.minimaxi.com/v1
  model: MiniMax-M2.7
  request_timeout_seconds: 300
  retry_attempts: 2
```

如果你想切到 `mlx-whisper`：

```yaml
asr:
  english_provider: mlx_whisper
  mlx_whisper_model: mlx-community/whisper-base.en-mlx
```

如果 YouTube 视频本身是中文，可以显式指定中文链路：

```bash
python3 -m video2post.cli video "YOUTUBE_URL" --lang zh --generate
```

这会输出 `transcript.zh.md`，并跳过英文翻译目标，直接基于中文转写稿生成内容素材和发布格式。

### 日常素材出稿

除了处理视频链接，也可以把日常想法、读书笔记、聊天内容或手动粘贴的 X 原推正文直接改写成 X 草稿：

```bash
video2post draft "原始内容" --mode x_engage --x-url "https://x.com/user/status/123"
video2post draft --x-url "https://x.com/user/status/123"
video2post draft "原始内容" --mode viral_280
```

`x_engage` 会生成回复候选、引用转发候选和独立短帖候选；`viral_280` 会生成一条 280 字符以内的短推。只给 X 链接时默认使用 `--x-fetch auto`：先通过 oEmbed 尝试抓取原推正文；如果原推只有外链，会继续尝试抓取外链页面的标题、摘要和正文段落；如果识别到 X Article 长文，会升级到 Chrome 登录态抓取。也可以用 `--x-fetch public` 禁用浏览器，或用 `--x-fetch browser` 强制浏览器模式。如果同时提供正文，X 链接只作为上下文保存。不会自动发布。

### 快速出稿模式

如果你只是想尽快拿到一版可编辑、可发布的二创草稿，可以使用 `--fast`：

```bash
video2post video URL --fast
```

`--fast` 会自动开启生成，不需要额外传 `--generate`。在未显式传 `--targets` 时，它只生成快速出稿所需的核心产物：`notes`、`x_article`、`x_thread`、`x_titles`、`publish_formats`。它会跳过标准模式默认的 `translation`、`article`、`script`、`titles`，因此更适合个人创作者先快速判断内容是否值得继续精修。

如果你在 `--fast` 下显式传了 `--targets`，系统会尊重你的选择：

```bash
video2post video URL --fast --targets notes,x_article
```

## 处理流程

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

## 输出示例

每个视频会生成一个独立输出目录：

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
    article.wechat.md
    article.wechat.html
    x_article.x.md
    x_article.x.txt
    cover.jpg
    cover.meta.json
    article.md
    script.md
    titles.md
```

文件说明：

- `meta.json`：视频信息、处理状态、模型信息和错误信息。
- `audio.wav`：标准化后的音频文件。
- `transcript.en.md`：YouTube 英文视频的英文逐字稿。
- `transcript.zh.md`：中文翻译或中文整理稿。
- `notes.md`：核心观点、技术概念、金句和二创角度。
- `x_article.md`：适合直接复制到 X 长文的中文成稿。
- `x_thread.md`：适合拆成 X thread 的短段版本。
- `x_titles.md`：适合 X 发布场景的开头钩子和标题候选。
- `article.wechat.md`：公众号发布前可编辑 Markdown 版本。
- `article.wechat.html`：可复制到微信公众号编辑器的 HTML 版本，内置适配公众号的 inline 样式。
- `x_article.x.md`：适合 X Articles 的 Markdown 发布版本。
- `x_article.x.txt`：适合直接粘贴到 X 长文编辑器的纯文本版本。
- `cover.jpg`：从视频截图适配出的封面图。
- `cover.meta.json`：封面图来源时间点、源链接和导出信息。
- `article.md`：技术博客或公众号长文草稿。
- `script.md`：短视频口播稿。
- `titles.md`：不同发布场景的标题候选。

## 技术路线

项目采用 Python 作为主语言，核心逻辑会沉淀为可复用 pipeline。CLI、Web 和桌面应用都只作为入口层，避免后续重复实现下载、转写和生成逻辑。

第一版推荐技术栈：

- Python
- Typer
- Pydantic
- yt-dlp
- ffmpeg
- faster-whisper
- mlx-whisper
- FunASR
- 云端大模型 API
- Markdown 文件输出

第一版优先支持 macOS，后续再考虑 Linux 和 Windows。核心 pipeline 会避免写死 macOS 专有路径，为后续跨平台留出空间。

第一版工程重点：

- 任务状态和断点续跑：每个阶段完成后落盘，失败后可从中间步骤继续。
- LLM Provider 抽象：优先支持 OpenAI-compatible API，后续可扩展其他云端模型或本地模型。
- Prompt 模板管理：将翻译、笔记、长文、口播稿和标题模板独立维护。
- 长视频分块处理：转写结果按 segment 保存，LLM 阶段分块总结再汇总生成。
- macOS 默认英文 ASR 当前使用 `mlx-whisper` + `mlx-community/whisper-base.en-mlx`。
- 其他系统默认仍使用 `faster-whisper base`。

第一版 MVP 验收重点：

- 能处理一个 YouTube 英文技术视频链接。
- 能生成 `meta.json`、`audio.wav`、`transcript.en.md`、`transcript.zh.md`、`notes.md`、`x_article.md`、`x_thread.md`、`x_titles.md` 和 `cover.jpg`。
- 失败时能记录失败阶段和错误信息。
- 已完成阶段可以跳过，支持后续重跑和重新生成二创内容。

当前推荐命令集：

```bash
video2post video URL
video2post task retry TASK_DIR
video2post task generate TASK_DIR --targets x_article,x_thread,x_titles
video2post task generate TASK_DIR --targets cover --cover-at 00:00:30
video2post doctor
video2post samples
video2post config show
```

## 安装与运行

macOS 下推荐先安装系统依赖：

```bash
brew install ffmpeg yt-dlp
```

然后在项目根目录安装 Python 依赖：

```bash
python3 -m pip install -e .[dev]
python3 -m pip install -e .[asr]
```

如果只想先确认 CLI 能不能跑起来，可以直接执行：

```bash
python3 -m video2post.cli --help
python3 -m video2post.cli samples
```

更完整的安装、配置和故障排查见：[docs/setup.md](docs/setup.md)。

- CLI 参数和场景速查：[docs/cli-usage.md](docs/cli-usage.md)

## 回归样例

当前项目内置了一组固定手工回归样例，可以直接查看：

```bash
video2post samples
```

样例说明文档见：[docs/samples.md](docs/samples.md)。
手工回归检查表见：[docs/manual-checklist.md](docs/manual-checklist.md)。

后续预留方向：

- Web 后端：FastAPI
- Web 前端：React / Vite
- 数据存储：SQLite
- 桌面应用：Tauri + React + Python sidecar

## ASR 方案

第一版会预留统一 ASR 接口，但实现顺序建议分阶段推进：

1. 优先跑通 `faster-whisper + YouTube`。
2. 再接入 `FunASR + B 站`。
3. 后续再考虑 WhisperX、说话人分离、词级时间戳等高级能力。

统一 ASR 输出结构应尽量保持稳定：

```text
segments:
  - start
  - end
  - text
  - language
```

## 大模型生成

第一版采用本地运行工具 + 云端大模型 API 的方式。

大模型主要负责：

- 英文转中文。
- 内容总结。
- 结构化整理。
- 技术长文生成。
- 短视频口播稿生成。
- 标题生成。

提示词需要明确约束：

- 不虚构事实。
- 不添加原视频没有的数据。
- 不直接搬运原文表达。
- 保持适合中文技术读者的表达。
- 明确区分原视频观点和整理者补充说明。

## 路线图

### 阶段一：CLI MVP

- 单链接处理。
- 支持 YouTube 和 B 站。
- 本地 ASR。
- 云端大模型生成二创内容。
- Markdown 文件输出。
- 支持阶段性重跑，避免失败后从头开始。

### 阶段二：个人 Web 工作台

- Web 页面粘贴链接。
- 查看任务进度。
- 在线查看和编辑逐字稿。
- 一键重新生成长文、口播稿和标题。
- 保存历史任务。

### 阶段三：桌面应用

- 更适合个人日常使用。
- 简化本地启动体验。
- 提供更完整的素材管理和编辑体验。

### 阶段四：素材库和检索

- 保存长期处理过的视频内容。
- 支持按主题、作者、关键词检索。
- 支持向量搜索。
- 支持同主题视频对比总结。

## 当前非目标

第一版暂不计划支持：

- 抖音、视频号等平台。
- 多用户系统。
- 登录、权限、计费。
- Web UI。
- 桌面客户端。
- 批量任务队列。
- 自动发布到公众号、微博、小红书、B 站等平台。
- 视频剪辑、自动配图、自动配音。
- 向量检索或长期素材库。

## 注意事项

本项目用于个人学习、整理和二次创作辅助。生成内容时应尊重原作者，避免直接搬运原视频表达，必要时标注来源。

视频平台规则可能变化，下载能力依赖 `yt-dlp` 的实际支持情况。部分平台或链接可能需要 Cookie，也可能出现下载失败。遇到平台下载不稳定时，可以先用其他方式保存为本地音频或视频文件，再交给 `video2post video ./local-file.mp4` 继续转写和出稿。

## 文档

- [需求文档](docs/requirements.md)
- [开发计划](docs/development-plan.md)
- [安装与运行](docs/setup.md)

### 发布格式转换

将任意 Markdown 文件转换为公众号和 X 长文发布格式：

```bash
video2post format article.md --platform wechat,x
video2post format article.md wechat,x
video2post format article.md --platform wechat --output ./publish-ready
```

也可以转换已有 task 目录中的产物：

```bash
video2post format ./outputs/2026-... --source article --platform wechat,x
```

生成文件包括：

```text
*.wechat.md
*.wechat.html
*.x.md
*.x.txt
```

默认只做确定性格式转换，不调用 LLM。需要平台化改写时显式使用 `--rewrite`。
