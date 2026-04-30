# video2post 真实验收产物对照

这份文档用于记录当前项目里已经真实跑过的任务目录，以及这些目录适合用来对照什么能力。

它和 [samples.md](./samples.md) 的区别是：

- `samples.md` 记录的是“推荐用哪些链接做回归”
- 本文档记录的是“已经真实生成过的产物目前在哪里”

## 使用建议

当你想确认某个功能是不是“真实跑通过”，优先看这里：

1. 找对应平台或场景
2. 打开对应任务目录
3. 对照关键产物文件
4. 再决定是否需要重新跑一条新任务

## 当前已知真实任务目录

### 1. YouTube 英文主链路

- 场景：YouTube 英文视频下载、英文转写、中文整理
- 任务目录：
  - [outputs/2026-04-30-learn-95-of-codex-in-30-minutes](/Users/yangxinglong/Documents/video2post/.worktrees/phase-0-cli-skeleton/outputs/2026-04-30-learn-95-of-codex-in-30-minutes)
- 可对照文件：
  - [audio.wav](/Users/yangxinglong/Documents/video2post/.worktrees/phase-0-cli-skeleton/outputs/2026-04-30-learn-95-of-codex-in-30-minutes/audio.wav)
  - [transcript.en.md](/Users/yangxinglong/Documents/video2post/.worktrees/phase-0-cli-skeleton/outputs/2026-04-30-learn-95-of-codex-in-30-minutes/transcript.en.md)
  - [transcript.zh.md](/Users/yangxinglong/Documents/video2post/.worktrees/phase-0-cli-skeleton/outputs/2026-04-30-learn-95-of-codex-in-30-minutes/transcript.zh.md)
  - [transcript.segments.json](/Users/yangxinglong/Documents/video2post/.worktrees/phase-0-cli-skeleton/outputs/2026-04-30-learn-95-of-codex-in-30-minutes/transcript.segments.json)
  - [meta.json](/Users/yangxinglong/Documents/video2post/.worktrees/phase-0-cli-skeleton/outputs/2026-04-30-learn-95-of-codex-in-30-minutes/meta.json)

适合验证：

- YouTube 主链路是否跑通
- 英文段落稿输出
- 中文整理稿是否落盘
- `transcript.segments.json` 是否保留原始分段

### 2. B 站中文最小链路

- 场景：B 站中文视频下载、中文转写、基础二创内容
- 任务目录：
  - [outputs/2026-04-30-untitled](/Users/yangxinglong/Documents/video2post/.worktrees/phase-0-cli-skeleton/outputs/2026-04-30-untitled)
- 可对照文件：
  - [audio.wav](/Users/yangxinglong/Documents/video2post/.worktrees/phase-0-cli-skeleton/outputs/2026-04-30-untitled/audio.wav)
  - [transcript.zh.md](/Users/yangxinglong/Documents/video2post/.worktrees/phase-0-cli-skeleton/outputs/2026-04-30-untitled/transcript.zh.md)
  - [notes.md](/Users/yangxinglong/Documents/video2post/.worktrees/phase-0-cli-skeleton/outputs/2026-04-30-untitled/notes.md)
  - [titles.md](/Users/yangxinglong/Documents/video2post/.worktrees/phase-0-cli-skeleton/outputs/2026-04-30-untitled/titles.md)
  - [transcript.segments.json](/Users/yangxinglong/Documents/video2post/.worktrees/phase-0-cli-skeleton/outputs/2026-04-30-untitled/transcript.segments.json)
  - [meta.json](/Users/yangxinglong/Documents/video2post/.worktrees/phase-0-cli-skeleton/outputs/2026-04-30-untitled/meta.json)

适合验证：

- B 站中文主链路是否跑通
- 中文稿是否直接可用于后续生成
- `notes.md` / `titles.md` 是否能从中文稿生成

说明：

- 这个目录创建时还没修复中文标题 slug，因此目录名仍是 `untitled`
- 后续新生成的 B 站任务目录应尽量接近真实中文标题

### 3. FunASR 实验任务目录

- 场景：B 站 + FunASR 真实环境验证
- 任务目录：
  - [outputs-funasr/2026-04-30-untitled](/Users/yangxinglong/Documents/video2post/.worktrees/phase-0-cli-skeleton/outputs-funasr/2026-04-30-untitled)
  - [outputs-funasr2/2026-04-30-untitled](/Users/yangxinglong/Documents/video2post/.worktrees/phase-0-cli-skeleton/outputs-funasr2/2026-04-30-untitled)

适合验证：

- FunASR 真实环境安装是否完成
- 音频阶段是否跑通
- 实验性 provider 的冷启动成本和推理表现

说明：

- 这两组目录主要用于技术排查，不作为当前默认中文链路的推荐对照
- 详细结论见：[funasr-validation.md](./funasr-validation.md)

## 后续维护建议

当出现新的“真实跑通任务”时，建议补充：

1. 平台和场景
2. 任务目录链接
3. 关键产物链接
4. 适合验证的能力
5. 是否存在已知限制
