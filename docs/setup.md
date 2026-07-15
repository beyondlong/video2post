# video2post 安装与运行

本文档用于说明当前 macOS 环境下，如何把 `video2post` 跑起来。

## 运行环境

当前第一版优先支持：

- macOS
- Python 3.11+
- `ffmpeg`
- `yt-dlp`

如果要跑英文转写，还需要安装：

- `faster-whisper`

如果你想在 Apple Silicon 上实验更快的英文转写，还可以安装：

- `mlx-whisper`

如果要实验 `FunASR` 中文 ASR，还需要额外安装：

- `funasr`
- `torch`
- `torchaudio`

## 1. 安装系统依赖

推荐使用 Homebrew：

```bash
brew install ffmpeg yt-dlp
brew install node
```

检查：

```bash
ffmpeg -version
yt-dlp --version
```

## 2. 安装 Python 依赖

在项目根目录执行：

```bash
python3 -m pip install -e '.[dev]'
python3 -m pip install -e '.[asr]'
```

如果你要实验 `mlx-whisper`：

```bash
python3 -m pip install -e '.[asr-mlx]'
```

如果你需要实验 `FunASR`：

```bash
python3 -m pip install -e '.[asr-chinese]'
python3 -m pip install torch torchaudio
```

## 3. 配置 LLM

在项目根目录创建 `.env`：

```bash
VIDEO2POST_LLM_API_KEY=your-key
VIDEO2POST_LLM_BASE_URL=https://api.minimaxi.com/v1
VIDEO2POST_LLM_MODEL=MiniMax-M2.7
```

也可以把部分配置放到 `config.yaml`：

```yaml
llm:
  base_url: https://api.minimaxi.com/v1
  model: MiniMax-M2.7
  request_timeout_seconds: 300
  retry_attempts: 2
```

如果你想显式指定非 macOS 环境下当前推荐的英文转写模型，也可以补：

```yaml
asr:
  faster_whisper_model: base
```

如果你想切到 `mlx-whisper`，可补：

```yaml
asr:
  english_provider: mlx_whisper
  mlx_whisper_model: mlx-community/whisper-base.en-mlx
```

当前 macOS 默认就会优先使用：

```yaml
asr:
  english_provider: mlx_whisper
  mlx_whisper_model: mlx-community/whisper-base.en-mlx
```

当前中文视频默认复用 `faster-whisper` 作为较轻量的兜底链路。如果你要实验 `FunASR`，可以显式补：

```yaml
asr:
  chinese_provider: funasr
  funasr_model: paraformer
```

如果视频平台是 YouTube、但视频语言是中文，请在处理命令中加 `--lang zh`：

```bash
python3 -m video2post.cli video "YOUTUBE_URL" --lang zh --generate
```

如果某些 YouTube 视频提示需要登录或确认不是机器人，建议在 `config.yaml` 里再补：

```yaml
download:
  cookies_from_browser: chrome
  js_runtimes: node
  remote_components: ejs:github
```

如果你的 YouTube 登录态在 Safari，就改成：

```yaml
download:
  cookies_from_browser: safari
  js_runtimes: node
  remote_components: ejs:github
```

## 4. 正确运行 CLI

推荐两种方式。

### 方式 A：安装后直接运行

如果你已经执行过：

```bash
python3 -m pip install -e .[dev]
```

那么可以直接运行：

```bash
video2post --help
video2post samples
```

### 方式 B：用 Python 模块方式运行

如果当前 shell 里的 `video2post` 命令还没有正确指向当前仓库，可以先用：

```bash
python3 -m video2post.cli --help
python3 -m video2post.cli samples
```

这个方式在本地开发、多个 worktree 并行时尤其稳。

## 5. 最小验证

### 查看命令是否正常

```bash
python3 -m video2post.cli --help
python3 -m video2post.cli samples
python3 -m video2post.cli doctor
python3 -m video2post.cli config show
```

### 跑一条 YouTube 样例

```bash
video2post video "https://www.youtube.com/watch?v=474wZZHoWN4" --output ./outputs-check --generate --targets notes,titles --cleanup-source
```

如果当前 shell 里的 `video2post` 没有绑定到当前仓库，可改用：

```bash
python3 -m video2post.cli video "https://www.youtube.com/watch?v=474wZZHoWN4" --output ./outputs-check --generate --targets notes,titles --cleanup-source
```


### 快速出稿模式

创作者快速试稿可以直接运行：

```bash
video2post video "YOUTUBE_OR_BILIBILI_URL" --fast --cleanup-source
```

`--fast` 会自动生成 `notes.md`、`x_article.md`、`x_thread.md`、`x_titles.md` 和发布格式文件，省去标准模式里的完整翻译稿、通用长文、脚本和标题候选。需要自定义快速产物时可以继续传 `--targets`，例如：

```bash
video2post video "YOUTUBE_OR_BILIBILI_URL" --fast --targets notes,x_article
```

### 跑一条 B 站样例

```bash
video2post video "https://www.bilibili.com/video/BV1fA9mBPEZt?t=7.0" --output ./outputs-check --generate --targets notes,titles --cleanup-source
```

同样，如果命令入口还没绑定成功，也可以用：

```bash
python3 -m video2post.cli video "https://www.bilibili.com/video/BV1fA9mBPEZt?t=7.0" --output ./outputs-check --generate --targets notes,titles --cleanup-source
```

更多回归方式见：

- [samples.md](./samples.md)
- [manual-checklist.md](./manual-checklist.md)

## 6. 常见问题

### 1. 直接运行 `video2post` 提示 `ModuleNotFoundError`

说明当前 shell 里的命令没有绑定到这个仓库的可编辑安装。

处理方式：

```bash
python3 -m pip install -e .[dev]
```

或者先改用：

```bash
python3 -m video2post.cli --help
```

### 2. `doctor` 提示缺少依赖

先运行：

```bash
python3 -m video2post.cli doctor
```

如果缺的是系统命令，优先补：

```bash
brew install ffmpeg yt-dlp
```

如果缺的是 Python 包，重新执行：

```bash
python3 -m pip install -e '.[dev]'
python3 -m pip install -e '.[asr]'
```

### 3. 生成 `article.md` / `script.md` 时超时

当前项目已经支持 LLM 请求超时和瞬时断线重试。默认值：

```text
request_timeout_seconds=300
retry_attempts=2
```

如果你的 provider 仍然偏慢，可以继续调大：

```yaml
llm:
  request_timeout_seconds: 600
  retry_attempts: 3
```

### 4. B 站任务目录是 `untitled`

旧任务目录可能仍然保留历史命名。当前版本已经支持保留中文标题 slug，新任务目录应更接近真实视频标题。

### 5. `yt-dlp` 或 `ffmpeg` 命令找不到

说明系统依赖还没装好，或者当前 shell 没拿到 PATH。

处理方式：

```bash
brew install ffmpeg yt-dlp
ffmpeg -version
yt-dlp --version
```

如果是新开的 shell 仍然找不到，先重开一个终端窗口再试。

### 6. `FunASR` 很慢或者第一次下载很大

这是当前已知现象。`FunASR` 在 macOS 上首次冷启动会拉较大的模型文件。

当前中文 ASR 推荐策略：

- **默认**：`faster_whisper`（轻量、稳定、无额外依赖）
- **实验**：`funasr`（中文识别质量更好，但首次加载慢、依赖较重）

如果 FunASR 加载失败，pipeline 会自动回退到 `faster_whisper`，不会中断任务。

如果你只是想先稳定跑通 MVP，建议优先沿用当前默认链路：

```yaml
asr:
  chinese_provider: faster_whisper
  faster_whisper_model: base
```

确认环境稳定后再切换到 FunASR：

```yaml
asr:
  chinese_provider: funasr
  funasr_model: paraformer
```

### 7. YouTube 提示 `Sign in to confirm you’re not a bot`

这通常不是项目代码坏了，而是 YouTube 对当前请求要求更强的登录态或浏览器环境。

建议按这个顺序处理：

```bash
brew install node
```

然后在项目根目录创建 `config.yaml`：

```yaml
download:
  cookies_from_browser: chrome
  js_runtimes: node
  remote_components: ejs:github
```

如果你的 YouTube 登录态在 Safari，就改成 `safari`。
