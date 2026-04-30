# video2post 固定测试样例

本文档用于记录当前项目手工回归时优先使用的固定样例。目标不是覆盖所有边界，而是让每次关键改动后，都有一组稳定、可重复的验收入口。

## 推荐样例

### 1. YouTube 短技术视频

- 名称：`youtube-short-tech`
- 用途：YouTube 英文主链路验收
- 链接：`https://www.youtube.com/watch?v=474wZZHoWN4`
- 重点检查：
  - 元数据提取
  - 音频下载与标准化
  - `transcript.en.md`
  - `transcript.zh.md`
  - `notes.md` / `titles.md`

### 2. YouTube 长链路样例

- 名称：`youtube-long-tech`
- 用途：长视频分块与汇总链路验收
- 链接：`https://www.youtube.com/watch?v=474wZZHoWN4`
- 说明：
  - 当前阶段可先复用真实 YouTube 样例验证分块代码路径
  - 后续建议替换为更长、更稳定的英文技术视频样例

### 3. B 站中文最小链路样例

- 名称：`bilibili-short-cn`
- 用途：B 站中文主链路最小验收
- 链接：`https://www.bilibili.com/video/BV1fA9mBPEZt?t=7.0`
- 重点检查：
  - 中文标题任务目录
  - `audio.wav`
  - `transcript.zh.md`
  - `notes.md`
  - `titles.md`

### 4. B 站第二条真实样例

- 名称：`bilibili-second-cn`
- 用途：B 站第二条真实验收 / 中文 ASR 方案对比
- 链接：`https://www.bilibili.com/video/BV1A99yBYEZd?t=9.6`
- 说明：
  - 已用于 `FunASR` 真实环境验收
  - 当前更适合作为“中文链路 + provider 实验”样例

### 5. 无效链接样例

- 名称：`invalid-url`
- 用途：失败路径验收
- 链接：`https://example.com/video`
- 重点检查：
  - 平台识别为 `unknown`
  - `meta.json` 失败状态
  - 错误信息落盘

## 推荐回归顺序

每次关键改动后，优先做下面这些检查：

1. `video2post --help`
2. `video2post samples`
3. 跑一条 YouTube 样例
4. 跑一条 B 站样例
5. 跑局部重生成
6. 跑 `retry`
7. 跑一条失败路径

## CLI 查看方式

也可以直接用命令查看当前内置样例：

```bash
video2post samples
```
