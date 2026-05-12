# video2post CLI 使用速查

这份文档按日常使用场景整理命令。所有命令都可以用 `video2post ...`，如果本机命令入口还没绑定到当前仓库，就改用 `python3 -m video2post.cli ...`。

## 常用命令

### 1. 快速出稿

适合创作者先快速拿到一版可编辑稿件。

```bash
video2post video "VIDEO_URL" --fast --cleanup-source
```

`--fast` 会自动开启生成，不需要再加 `--generate`。默认生成：

- `notes.md`
- `x_article.md`
- `x_thread.md`
- `x_titles.md`
- `*.wechat.md` / `*.wechat.html`
- `*.x.md` / `*.x.txt`

如果只想要部分产物：

```bash
video2post video "VIDEO_URL" --fast --targets notes,x_article
```

### 2. 标准完整处理

适合需要完整中间稿和多种内容形态的场景。

```bash
video2post video "VIDEO_URL" --generate --cleanup-source
```

标准默认 targets 来自 `config.yaml` 的 `generation.default_targets`。默认包含 `translation`、`notes`、X 产物、通用长文、脚本、标题和发布格式。

### 3. 只下载和转写，不生成内容

```bash
video2post video "VIDEO_URL" --output ./outputs-check
```

这会创建任务目录、下载音频、生成转写稿，但不会调用 LLM 生成二创内容。

### 4. 中文 YouTube 视频

YouTube 默认按英文链路处理。如果视频本身是中文，加 `--lang zh`：

```bash
video2post video "YOUTUBE_URL" --lang zh --fast --cleanup-source
```

这会输出 `transcript.zh.md`，并跳过英文翻译默认目标。

### 5. 指定输出目录

```bash
video2post video "VIDEO_URL" --output ./outputs-check --fast
```

### 6. 生成封面截图

```bash
video2post video "VIDEO_URL" --generate --targets cover --cover-at 00:00:30
```

对已有任务重新生成封面：

```bash
video2post task generate TASK_DIR --targets cover --cover-at 00:00:30
```

### 7. 日常素材生成 X 草稿

把日常想法、读书笔记、聊天内容或手动粘贴的 X 原推正文改写成 X 发布素材：

```bash
video2post draft "原始内容" --mode x_engage --x-url "https://x.com/user/status/123"
video2post draft --x-url "https://x.com/user/status/123"
video2post draft "https://x.com/user/status/123" --mode viral_280
```

如果只给 X 链接，系统默认使用 `--x-fetch auto`：先通过 X 官方 oEmbed 接口尝试抓取原推正文；如果原推只有外链，会继续尝试抓取外链页面的标题、摘要和正文段落；如果识别到 X Article 长文，会升级到 Chrome 登录态抓取，再生成草稿。`x_engage` 会在 `drafts/YYYY-MM-DD-.../` 下生成：

- `source.md`
- `brief.md`
- `x_replies.md`
- `x_quote.md`
- `x_posts.md`
- `meta.json`

如果只想生成一条 280 字符以内的爆款短推：

```bash
video2post draft "原始内容" --mode viral_280
```

`--x-url` 会在缺少正文时尝试抓取原推正文；默认 `--x-fetch auto` 会在公开抓取失败且识别为 X Article 时升级到 Chrome 登录态抓取；如果同时提供正文，则只作为上下文保存。不会自动发布。

### 8. 对已有任务重新生成内容

```bash
video2post task generate TASK_DIR --targets notes,x_article,x_thread,x_titles,publish_formats
```

常见例子：

```bash
video2post task generate TASK_DIR --targets publish_formats
video2post task generate TASK_DIR --targets x_article,x_thread,x_titles
video2post task generate TASK_DIR --targets article,script,titles
```

### 9. 失败后继续跑

如果音频或转写已经存在，只想补后续缺失步骤：

```bash
video2post task retry TASK_DIR --generate --targets notes,x_article
```

### 10. 单独把 Markdown 转发布格式

普通 Markdown 文件：

```bash
video2post format article.md --platform wechat,x
```

已有任务目录中的稿件：

```bash
video2post format TASK_DIR --source x_article --platform wechat,x
```

## Target 速查

| Target | 输出文件 | 说明 |
| --- | --- | --- |
| `translation` | `transcript.zh.md` | 英文转写稿的中文翻译/整理稿。中文来源默认跳过。 |
| `notes` | `notes.md` | 内容笔记和要点整理。 |
| `x_article` | `x_article.md` | 适合 X Articles 的长文稿。 |
| `x_thread` | `x_thread.md` | 适合拆成 X thread 的短段内容。 |
| `x_titles` | `x_titles.md` | X 发布标题/钩子候选。 |
| `article` | `article.md` | 通用文章/公众号长文草稿。 |
| `script` | `script.md` | 视频口播脚本草稿。 |
| `titles` | `titles.md` | 通用标题候选。 |
| `cover` | `cover.jpg`, `cover.meta.json` | 从视频截图生成封面素材。 |
| `publish_formats` | `*.wechat.md`, `*.wechat.html`, `*.x.md`, `*.x.txt` | 把已有稿件转成公众号和 X 发布格式。 |

## 命令参考

### `video`

完整处理一个视频 URL。

```bash
video2post video URL [OPTIONS]
```

常用参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--config -c PATH` | `config.yaml` | 指定配置文件。 |
| `--output -o PATH` | 配置中的 `app.output_dir` | 指定输出目录。 |
| `--lang auto/en/zh` | `auto` | 指定源视频语言。中文 YouTube 用 `--lang zh`。 |
| `--download / --no-download` | download | 是否下载并规范化音频。 |
| `--transcribe / --no-transcribe` | transcribe | 是否运行 ASR。 |
| `--generate / --no-generate` | no-generate | 是否生成二创内容。 |
| `--fast / --standard` | standard | 快速出稿模式；自动生成核心 targets。 |
| `--targets TEXT` | 空 | 逗号分隔生成目标，例如 `notes,x_article`。 |
| `--cover-at TEXT` | 空 | 封面截图时间点，例如 `00:00:30`。 |
| `--cleanup-source / --keep-source` | 配置中的 `app.cleanup_source` | 音频规范化后是否删除压缩源文件。 |

注意：`--fast` 只在 `video` 命令中生效。它不会改变 `task generate TASK_DIR` 的行为。

### `draft`

把命令行粘贴的原始文本改写成 X 草稿。

```bash
video2post draft "原始内容" --mode x_engage
video2post draft "原始内容" --mode viral_280
video2post draft --x-url "https://x.com/user/status/123"
```

参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--config -c PATH` | `config.yaml` | 指定配置文件。 |
| `--mode TEXT` | `x_engage` | 草稿模式：`x_engage` 或 `viral_280`。 |
| `--x-url TEXT` | 空 | 可选 X 链接。缺少正文时会尝试抓取原推正文。 |
| `--x-fetch TEXT` | `auto` | X 抓取模式：`auto` 先公开抓取，遇到 X Article 再用 Chrome 登录态；`public` 只公开抓取；`browser` 强制 Chrome 登录态。 |
| `--output -o PATH` | `./drafts` | 草稿库根目录。 |
| `--title TEXT` | 空 | 用于生成本地目录名的标题。 |

输出：

- `x_engage`：`source.md`、`brief.md`、`x_replies.md`、`x_quote.md`、`x_posts.md`、`meta.json`。
- `viral_280`：`source.md`、`brief.md`、`viral_280.md`、`meta.json`。

`viral_280.md` 会做本地 280 字符校验，超长时任务标记失败，不写入超长推文。

### `task generate`

对已有任务目录重新生成内容。

```bash
video2post task generate TASK_DIR --targets notes,x_article
```

参数：

| 参数 | 说明 |
| --- | --- |
| `--config -c PATH` | 指定配置文件。 |
| `--targets TEXT` | 逗号分隔生成目标。为空时使用默认 targets。 |
| `--cover-at TEXT` | 生成 `cover` 时指定截图时间点。 |

### `task retry`

从已有任务目录恢复缺失步骤。

```bash
video2post task retry TASK_DIR --generate --targets notes
```

参数：

| 参数 | 说明 |
| --- | --- |
| `--config -c PATH` | 指定配置文件。 |
| `--generate / --no-generate` | 补齐音频/转写后是否继续生成内容。 |
| `--targets TEXT` | 生成目标。 |
| `--cover-at TEXT` | 封面截图时间点。 |

### `format`

把一个 Markdown 文件转换成发布格式。

```bash
video2post format article.md --platform wechat,x --output ./publish
```

参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--platform TEXT` | `wechat,x` | 发布平台，目前支持 `wechat` 和 `x`。 |
| `--output -o PATH` | 输入文件所在目录 | 输出目录。 |
| `--rewrite` | false | 预留的 LLM 重写开关；当前 deterministic 格式化建议不使用。 |

### `format` for task directories

从任务目录中选择已有稿件转换为发布格式。

```bash
video2post format TASK_DIR --source x_article --platform wechat,x
```

参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--source TEXT` | 平台默认源 | 可选 `article`、`x_article`、`notes`、`transcript`。 |
| `--platform TEXT` | `wechat,x` | 发布平台。 |
| `--output -o PATH` | 任务目录 | 输出目录。 |
| `--rewrite` | false | 预留的 LLM 重写开关。 |

默认源规则：

- WeChat 优先使用 `article.md`，没有时 fallback 到 `x_article.md`。
- X 优先使用 `x_article.md`，没有时 fallback 到 `article.md`。

### `task list`

列出最近任务和已有产物。

```bash
video2post task list --output ./outputs-check --limit 20
```

参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--config -c PATH` | `config.yaml` | 指定配置文件。 |
| `--output -o PATH` | 配置中的输出目录 | 任务输出目录。 |
| `--limit INTEGER` | `10` | 最多显示多少个任务。 |

### `doctor` / `samples` / `config show`

```bash
video2post doctor
video2post samples
video2post config show
video2post config show --config config.fast.yaml
```

- `doctor`：检查本地依赖。
- `samples`：列出内置手工回归样例。
- `config show`：打印最终生效配置。

## 推荐工作流

### 创作者快速试稿

```bash
video2post video "VIDEO_URL" --fast --cleanup-source
```

如果结果值得精修，再补完整稿件：

```bash
video2post task generate TASK_DIR --targets article,script,titles
video2post task generate TASK_DIR --targets publish_formats
```

### 长视频稳妥处理

```bash
video2post video "VIDEO_URL" --output ./outputs-check --generate --cleanup-source
```

长稿会自动使用 chunk 摘要和全局摘要链路；已有 chunk summary 会被复用。

### 只重做发布格式

```bash
video2post task generate TASK_DIR --targets publish_formats
```

这不会重新下载、转写或调用 LLM 生成正文，只会基于已有 `article.md` / `x_article.md` 输出发布格式。

## 故障排查提示

- YouTube 提示登录或机器人校验：在 `config.yaml` 配置 `download.cookies_from_browser: chrome` 或 `safari`。
- 中文 YouTube 识别成英文链路：加 `--lang zh`。
- 只想重新生成某个文件：优先用 `task generate TASK_DIR --targets ...`。
- 不想保留下载源文件：加 `--cleanup-source`。
- 当前 shell 找不到 `video2post`：改用 `python3 -m video2post.cli ...`。
