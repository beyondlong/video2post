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

如果要实验 `FunASR` 中文 ASR，还需要额外安装：

- `funasr`
- `torch`
- `torchaudio`

## 1. 安装系统依赖

推荐使用 Homebrew：

```bash
brew install ffmpeg yt-dlp
```

检查：

```bash
ffmpeg -version
yt-dlp --version
```

## 2. 安装 Python 依赖

在项目根目录执行：

```bash
python3 -m pip install -e .[dev]
python3 -m pip install -e .[asr]
```

如果你需要实验 `FunASR`：

```bash
python3 -m pip install -e .[asr-chinese]
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
python3 -m video2post.cli config show
```

### 跑一条 YouTube 样例

```bash
video2post process "https://www.youtube.com/watch?v=474wZZHoWN4" --output ./outputs-check --generate --targets notes,titles --cleanup-source
```

如果当前 shell 里的 `video2post` 没有绑定到当前仓库，可改用：

```bash
python3 -m video2post.cli process "https://www.youtube.com/watch?v=474wZZHoWN4" --output ./outputs-check --generate --targets notes,titles --cleanup-source
```

### 跑一条 B 站样例

```bash
video2post process "https://www.bilibili.com/video/BV1fA9mBPEZt?t=7.0" --output ./outputs-check --generate --targets notes,titles --cleanup-source
```

同样，如果命令入口还没绑定成功，也可以用：

```bash
python3 -m video2post.cli process "https://www.bilibili.com/video/BV1fA9mBPEZt?t=7.0" --output ./outputs-check --generate --targets notes,titles --cleanup-source
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

### 2. 生成 `article.md` / `script.md` 时超时

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

### 3. B 站任务目录是 `untitled`

旧任务目录可能仍然保留历史命名。当前版本已经支持保留中文标题 slug，新任务目录应更接近真实视频标题。

### 4. `yt-dlp` 或 `ffmpeg` 命令找不到

说明系统依赖还没装好，或者当前 shell 没拿到 PATH。

处理方式：

```bash
brew install ffmpeg yt-dlp
ffmpeg -version
yt-dlp --version
```

如果是新开的 shell 仍然找不到，先重开一个终端窗口再试。

### 5. `FunASR` 很慢或者第一次下载很大

这是当前已知现象。`FunASR` 在 macOS 上首次冷启动会拉较大的模型文件，当前更适合作为实验性 provider，而不是默认中文 ASR。

如果你只是想先稳定跑通 MVP，建议优先沿用当前默认链路，不要把 `FunASR` 设为首选。
