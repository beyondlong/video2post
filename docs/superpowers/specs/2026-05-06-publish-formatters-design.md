# 发布格式转换器设计

日期：2026-05-06
状态：已确认需求，待实现

## 背景

`video2post` 现在已经可以生成 `article.md`、`x_article.md` 等 Markdown 草稿。这些文件适合作为编辑稿，但还不是最终可以直接投放到平台编辑器里的发布格式。因此需要新增一层独立的格式转换能力，把 Markdown 内容转换成适合微信公众号和 X 长文发布流程的产物。

这个功能需要支持两类工作流：

1. 转换任意本地 Markdown 文件。
2. 转换 `video2post` 任务目录中已经生成的产物。

第一阶段优先做任意本地 Markdown 文件，因为它更通用，也更容易测试。任务产物转换应该复用同一套 formatter，不重复实现转换逻辑。

## 已确认需求

- 先支持任意本地 Markdown 文件转换。
- 再支持转换已有 task 目录中的产物。
- 微信公众号输出两份文件：可编辑 Markdown 版本和最终 HTML 版本。
- X 长文输出两份文件：Markdown 版本和纯文本版本。
- 默认只做确定性格式转换，不调用 LLM。
- 仍然需要支持 LLM 平台化改写，但必须通过 `--rewrite` 这类显式参数开启。
- 第一版只支持常用 Markdown：
  - 标题
  - 段落
  - 加粗和斜体
  - 有序列表和无序列表
  - 引用块
  - fenced code block
  - 图片
  - 链接
  - 分割线
- 第一版微信公众号 HTML 使用固定的清爽技术博主公众号风格，不做主题系统。

## 第一版非目标

- 自动发布到微信公众号或 X。
- 完整支持脚注、任务列表、数学公式等 Markdown 扩展语法。简单 Markdown 表格在第一版支持。
- 可配置的微信公众号主题系统。
- 追求在所有第三方 Markdown 编辑器中像素级一致。
- 默认进行内容改写。

这些能力可以在确定性转换链路稳定后再逐步加入。

## 推荐方案

在项目内部实现一套自包含的 Python formatter。外部转换器或本地 skills 可以作为参考，但实现不应该依赖独立的 Bun 或外部脚本运行时。

这样可以让项目保持可移植、可测试：

- `pipeline` 继续负责视频、音频、转写和内容生成。
- `formatter` 负责把 Markdown 转成平台发布格式。
- CLI 命令只解析参数并调用 formatter API，不在 CLI 层塞转换逻辑。

## CLI 设计

### 转换任意 Markdown 文件

```bash
video2post format path/to/article.md --platform wechat,x
```

默认输出到输入文件所在目录。

输入文件：

```text
article.md
```

预期输出：

```text
article.wechat.md
article.wechat.html
article.x.md
article.x.txt
```

命令也需要支持指定输出目录：

```bash
video2post format article.md --platform wechat --output ./publish-ready
```

### 转换已有任务产物

```bash
video2post format-task ./outputs/2026-... --source article --platform wechat,x
```

`--source` 支持任务产物名，例如：

```text
article
x_article
notes
transcript
```

推荐默认值：

- `wechat` 默认使用 `article.md`。
- `x` 默认优先使用 `x_article.md`；如果不存在，则回退到 `article.md`。

### 可选 LLM 改写

```bash
video2post format article.md --platform wechat,x --rewrite
```

默认行为只做确定性格式转换。启用 `--rewrite` 后，命令可以调用已配置的 LLM provider，在写入最终产物前对语气、节奏和平台适配做改写。

## 输出设计

### 微信公众号 Markdown

`*.wechat.md` 是可编辑的中间产物。它应该保留文章结构，同时应用一些公众号友好的约定：

- 必要时规范标题层级。
- 保持段落可读，避免过长段落。
- 保留代码围栏。
- 保留图片引用。
- 在直接内联外链不合适时，把普通外链转换为文末引用。
- 不在 Markdown 文件中混入视觉样式 HTML。

### 微信公众号 HTML

`*.wechat.html` 是用于复制到公众号编辑器的最终产物。它应该使用内联 CSS，因为公众号编辑器经常会剥离或隔离外部样式。

第一版样式固定为清爽技术博主公众号风格：

- 技术文章语气。
- 舒适的行高。
- 清晰的标题层级，避免过重的黑底标题。
- 采用暖纸面背景、暖灰边框和棕橙重点色，保持背景色、重点卡片、表格和代码块的视觉统一。
- 引用块渲染为轻量提示卡片。
- 无语言代码块按内容识别为“清单 / 要点 / 说明”卡片，避免把说明性内容误渲染成代码。
- 代码块使用轻量背景和等宽字体。
- 简单 Markdown 表格渲染为内联样式表格。
- 链接使用公众号兼容的表达方式，普通外链优先做文末引用。
- 图片保留并使用响应式尺寸。

#### 微信技术文章风格参考

第一版微信公众号 HTML 风格可以借鉴现有 `baoyu-markdown-to-html` skill 中成熟的公众号发布经验，但 `video2post` 应保持自包含。这个 skill 只作为风格和行为参考，不作为运行时依赖。

值得借鉴的约定：

- 默认使用内联 CSS，确保生成的 HTML 复制到公众号编辑器后尽量保留样式。
- 使用清爽技术博主公众号布局：有明确标题区、克制的小节标题、提示/清单/要点卡片、代码语言标签、表格和正式的延伸阅读区。
- 标题处理要有辨识度但克制，尤其是 `h2` 小节标题。
- 中文阅读默认值要舒服：正文约 16px、较宽松行高、克制的段落间距。
- 代码块需要可读的等宽字体、轻量背景、内边距，并避免在移动端破坏阅读。
- 引用块应该像提示或评论说明；无语言代码块如果是步骤、映射或说明，应渲染为内容卡片，而不是普通代码盒子。
- 普通外链可以支持可选的文末引用；微信公众号文章链接在合适时保持内联。
- 图片输出保留源路径，并使用响应式尺寸。

第一版不借鉴的部分：

- 不把 Bun、`npx` 或 skill 脚本作为运行时依赖。
- 不做多主题系统。
- 不支持数学公式、PlantUML、alerts、infographics 等扩展语法。
- 不加载用户级 EXTEND.md 偏好配置。

目标是吸收这个 skill 中实用的公众号发布经验，然后在本项目里实现一套小而稳定的 Python formatter。

### X Markdown

`*.x.md` 保留结构，面向 X Articles 或其他支持 Markdown 的长文编辑器：

- 保留标题和轻量标题层级。
- 在有助于扫读时保留列表。
- 链接默认保留为 Markdown 链接，除非纯文本转换需要其他处理。
- 不引入公众号专用的文末引用，除非未来抽象出共享链接处理规则。

### X 纯文本

`*.x.txt` 是最稳妥的粘贴目标：

- 把 Markdown 标题转换成纯文本标题。
- 把链接转换成可读文本加 URL。
- 保持短段落。
- 把列表转换成纯文本项目符号或编号行。
- 移除粘贴后会显得噪音很大的 Markdown 语法。

## Formatter 架构

建议模块结构：

```text
video2post/formatters/
  __init__.py
  markdown_parser.py
  models.py
  wechat.py
  x_longform.py
  rewrite.py
```

职责划分：

- `markdown_parser.py`：把 Markdown 解析成轻量文档表示，或封装选定的 Markdown parser。
- `models.py`：定义 `FormatRequest`、`FormatResult`、`PlatformOutput` 等输入输出 dataclass。
- `wechat.py`：写入微信公众号 Markdown 和 HTML 产物。
- `x_longform.py`：写入 X Markdown 和纯文本产物。
- `rewrite.py`：只在开启 `--rewrite` 时使用的可选 LLM 改写集成。

CLI 应保持轻量：

- 解析路径和参数。
- 解析平台选择。
- 解析 task 产物源文件。
- 调用 formatter 函数。
- 打印生成文件路径。

## 数据流

### 任意 Markdown 文件

```text
input.md
  -> 可选 rewrite 步骤
  -> Markdown parser / 标准化文档
  -> 平台 formatter
  -> 在输入文件旁边或 --output 指定目录中生成文件
```

### 任务产物

```text
task dir
  -> 解析 source 产物
  -> 复用任意 Markdown 文件的 formatter 流程
  -> 在 task dir 或 --output 指定目录中生成文件
```

## 错误处理

formatter 应针对以下情况给出清晰错误信息：

- 输入文件不存在。
- 不支持的平台值。
- 使用 `format-task` 时任务目录缺少 `meta.json`。
- 指定的 source 产物不存在。
- 请求 `--rewrite` 但 LLM 凭证或配置缺失。
- Markdown parser 无法恢复的解析错误。

确定性格式转换失败时，第一版不修改 task metadata；除非后续决定把格式化状态也记录到 `meta.json`。

## 测试策略

单元测试应覆盖：

- CLI 平台参数解析。
- 输出文件名生成。
- 微信 Markdown 链接和文末引用转换。
- 微信 HTML 包含内联样式和预期结构。
- X Markdown 保留有用结构。
- X 纯文本移除噪音 Markdown 语法。
- `format-task` 的 source 默认解析逻辑。
- `--rewrite` 是显式 opt-in，默认格式化时不会调用 LLM。

Markdown fixture 应包含：

- 标题
- 段落
- 加粗和斜体
- 有序列表和无序列表
- 引用块
- fenced code block
- 图片
- 外部链接
- 分割线

## 实现阶段的待确认问题

- Markdown parser 选择：使用 `markdown-it-py`、Python Markdown，还是为第一版常用 Markdown 写一个最小 parser？
- 普通外链是否总是转换为微信公众号文末引用，还是做成 `--wechat-cite` 参数并默认开启？
- 生成的格式化产物未来是否要写入 task metadata，还是始终只作为普通文件存在？
- `format-task` 的输出文件名是否需要包含 source 名称，例如 `article.wechat.html` 和 `x_article.x.txt`，以避免冲突？

## 初始实现建议

建议按以下顺序实现：

1. 增加面向任意 Markdown 文件的确定性 formatting API。
2. 增加 `video2post format` CLI。
3. 增加微信公众号 Markdown 和 HTML 输出。
4. 增加 X Markdown 和纯文本输出。
5. 增加复用同一套 API 的 `video2post format-task`。
6. 在确定性路径有测试覆盖后，再增加可选的 `--rewrite`。
