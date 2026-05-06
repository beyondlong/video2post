# 发布格式转换器

`video2post` 支持把 Markdown 内容转换为微信公众号和 X 长文发布格式。

## 任意 Markdown 文件

```bash
video2post format article.md --platform wechat,x
```

默认输出到输入文件所在目录：

```text
article.wechat.md
article.wechat.html
article.x.md
article.x.txt
```

可以使用 `--output` 指定输出目录：

```bash
video2post format article.md --platform wechat --output ./publish-ready
```

## Task 产物

```bash
video2post format-task ./outputs/2026-... --source article --platform wechat,x
```

`--source` 可选：

- `article`
- `x_article`
- `notes`
- `transcript`

不指定 `--source` 时：

- `wechat` 默认使用 `article.md`。
- `x` 默认优先使用 `x_article.md`，不存在时回退到 `article.md`。

## 输出说明

- `*.wechat.md`：公众号友好的可编辑 Markdown 中间稿。
- `*.wechat.html`：可复制到公众号编辑器的 HTML，使用内联 CSS。
- `*.x.md`：保留 Markdown 结构的 X 长文稿。
- `*.x.txt`：适合直接粘贴的纯文本版本。

## 微信样式

第一版公众号 HTML 以“清爽技术博主公众号 + X 长文”为风格方向，借鉴 `baoyu-markdown-to-html` 的发布经验，但不依赖 Bun、npx 或 skill 脚本。

样式目标：

- 清爽技术博主公众号风格，避免固定口号和过重的黑底标题。
- 采用暖纸面背景、暖灰边框和棕橙重点色，保持背景色、重点卡片、表格和代码块的视觉统一。
- 正文约 16px，行高舒适。
- 标题层级清晰但克制，H2 使用浅底色和左侧强调线形成视觉锚点。
- 代码块使用轻量背景、等宽字体和移动端友好的换行。
- 引用块渲染为“提示”卡片，无语言代码块会按内容识别为“清单 / 要点 / 说明”。
- Markdown 表格渲染为内联样式表格，适合复制到公众号编辑器。
- 普通外链默认转为文末引用。

## Rewrite

默认转换不调用 LLM。

`--rewrite` 是显式 opt-in，目前保留为改写钩子；确定性转换链路可独立使用和测试。

## 第一版支持的 Markdown

- 标题
- 段落
- 加粗和斜体
- 有序列表和无序列表
- 引用块
- fenced code block
- 图片
- 链接
- 分割线
- 表格

## 第一版暂不支持
- 脚注
- 任务列表
- 数学公式
- PlantUML
- Infographics
- 自动发布到平台
