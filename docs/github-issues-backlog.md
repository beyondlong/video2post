# video2post GitHub Issue Backlog

这份文档用于整理 `video2post` 当前剩余功能的 GitHub issue 草稿，方便后续批量创建到仓库中。

当前建议优先创建以下 7 个议题。

---

## 1. Refine long-video chunking and hierarchical summarization

### Background

`video2post` 已经具备基础版长视频分块处理能力：

- 超长转写稿会拆分到 `chunks/`
- 每个 chunk 会生成局部摘要到 `summaries/`
- 最终生成阶段会优先使用摘要而不是完整原稿

这条链路已经可用，但对于 30-90 分钟技术视频仍然需要进一步增强稳定性和质量。

### Goal

让长视频处理更稳定，同时减少 LLM 上下文压力。

### Scope

- 优化按 ASR segment 切块的策略
- 尽量避免在语义中间截断
- 支持更清晰的分层摘要流程
  - chunk summary
  - merged/global summary
  - final content generation
- 保留中间产物，方便人工检查
- 复用已有 chunk summary，避免重复花费

### Acceptance Criteria

- 长转写稿会在合理边界上切块
- 非常长的视频也能稳定生成 `notes.md`、`x_article.md`、`x_thread.md`、`x_titles.md`
- 已存在的 `summaries/*.summary.md` 会被复用
- 自动化测试覆盖切块与摘要汇总行为

---

## 2. Add `--fast` quick-draft mode for creator workflow

### Background

当前 CLI 已经能跑完整链路，但对于个人创作者场景，“尽快出一版可用稿”很重要。此前已经讨论过 `--fast` 模式，但还未正式落地。

### Goal

提供一条“更快出稿、略降精度”的处理模式，优先服务创作者快速试内容。

### Scope

- 新增 `--fast` CLI 模式
- 使用更轻的 ASR / 更少默认产物
- 减少不必要的中间阶段
- 优先输出：
  - 中文整理稿
  - `notes.md`
  - `x_article.md`
  - `x_thread.md`
  - `x_titles.md`
- 保留与标准模式共存的配置方式

### Acceptance Criteria

- `video2post process URL --fast` 可运行
- 相比标准模式，整体处理时间明显缩短
- 输出结果仍足够支撑二创和 X 发布
- 文档中清晰说明 `--fast` 与标准模式差异

---

## 3. Improve Bilibili Chinese pipeline and stabilize FunASR

### Background

当前 B 站最小链路已经跑通：

- 链接识别
- 音频下载与标准化
- 中文转写
- `notes/article/script/titles` 生成

`FunASR` 也已经接入，但当前更适合作为实验性 provider，还不够稳。

### Goal

把 B 站中文链路从“最小可用”推进到“更稳定、更正式可用”。

### Scope

- 增加更多真实 B 站样例验收
- 明确默认中文 ASR 路线
- 稳定 `FunASR` provider
- 优化中文稿件生成质量
- 完善 B 站 `retry`、任务状态和错误恢复表现

### Acceptance Criteria

- 至少增加 2-3 条真实 B 站样例回归
- `FunASR` 或默认中文链路在长音频下表现可接受
- B 站链路文档和样例同步完善
- 自动化测试覆盖 provider 选择和中文任务续跑

---

## 4. Support local audio/video file input as a first-class source

### Background

当前主链路以 YouTube / B 站链接为主，但真实使用中，创作者也会有：

- 已下载的视频文件
- 本地音频素材
- 平台限制难以直接抓取的内容

### Goal

支持把本地音频/视频文件作为正式输入源，而不是只依赖平台下载。

### Scope

- 新增本地文件输入命令或参数
- 识别本地音频与视频
- 视频自动提取音频
- 统一接入现有任务目录和 pipeline
- 在 `meta.json` 中记录本地来源信息

### Acceptance Criteria

- 可以处理本地 `mp4` / `mov` / `wav` / `mp3`
- 本地文件输入可复用现有转写、生成、重试逻辑
- 文档说明清楚本地输入与 URL 输入的差异
- 自动化测试覆盖本地输入主路径

---

## 5. Improve X cover generation with multi-candidate selection

### Background

当前 `cover.jpg` MVP 已经支持：

- 从视频中按时间点截图
- 输出 `cover.jpg`
- 输出 `cover.meta.json`

但第一版仍然偏基础，缺少更适合发布使用的选帧能力。

### Goal

让 X 封面图生成更智能、更适合真实发布。

### Scope

- 支持多候选封面生成
- 增加默认选帧策略
- 尝试避开纯黑帧、转场帧、模糊帧
- 优化输出比例与导出命名
- 扩展 `cover.meta.json` 记录更多候选信息

### Acceptance Criteria

- 可生成多张候选封面
- 默认策略能明显减少无效截图
- `cover.meta.json` 包含候选帧来源时间点和选择信息
- 文档中补充推荐使用方式

---

## 6. Improve downloader / ASR / LLM error diagnostics and recovery UX

### Background

当前项目已经修过一批真实问题：

- YouTube cookies / JS runtime / remote components
- LLM timeout / retry
- provider 运行时错误写回 `meta.json`

但整体错误体验仍然可以更友好，尤其是给个人用户自助排查时。

### Goal

让下载、转写、生成失败时的提示更可理解、更好恢复。

### Scope

- 优化 CLI 错误信息输出
- 对典型错误给出更明确建议
- 强化 `meta.json` 里的失败上下文
- 明确哪些失败可 `retry`
- 补充 `doctor` 或文档中的常见问题

### Acceptance Criteria

- 常见下载/ASR/LLM 失败信息可读性明显提升
- `retry` 对可恢复错误更友好
- 文档中有更完整的排障说明
- 回归测试覆盖关键错误分支

---

## 7. Build a lightweight task browser and local workspace UI

### Background

当前 `video2post` 主要是 CLI-first。虽然已经有：

- `tasks`
- `samples`
- 手工回归文档
- 真实任务目录

但随着任务和产物增多，纯文件夹浏览开始不够顺手。

### Goal

提供一个轻量本地工作台，方便浏览任务、查看产物、快速复制 X 发布内容。

### Scope

- 设计简单本地 Web 工作台或任务浏览界面
- 浏览任务列表与状态
- 预览关键产物：
  - `transcript.*`
  - `notes.md`
  - `x_article.md`
  - `x_thread.md`
  - `x_titles.md`
  - `cover.jpg`
- 支持快速打开任务目录或复制内容

### Acceptance Criteria

- 能在本地浏览已有任务及状态
- 至少支持查看 X 向核心产物
- 不引入复杂登录/后端依赖
- 保持与当前文件目录结构兼容

