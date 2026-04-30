# video2post 手工回归检查表

这份检查表服务于日常开发后的快速验收。目标不是做完整 QA，而是用最短路径确认主链路没有被改坏。

固定样例清单见：[samples.md](./samples.md)

## 每次改动后的最小检查

1. CLI 是否正常

```bash
video2post --help
video2post samples
video2post doctor
video2post config show
```

重点看：

- 命令是否能正常输出
- 是否包含 `process / retry / generate / tasks / samples / config`

2. YouTube 主链路

推荐样例：`youtube-short-tech`

```bash
video2post process "https://www.youtube.com/watch?v=474wZZHoWN4" --output ./outputs-check --generate --targets notes,titles --cleanup-source
```

重点检查：

- 生成任务目录
- `meta.json`
- `audio.wav`
- `transcript.en.md`
- `notes.md`
- `titles.md`

状态预期：

- 至少进入 `notes_generated` 或 `titles_generated`
- 如果默认全套生成，则应为 `completed`

3. B 站中文链路

推荐样例：`bilibili-short-cn`

```bash
video2post process "https://www.bilibili.com/video/BV1fA9mBPEZt?t=7.0" --output ./outputs-check --generate --targets notes,titles --cleanup-source
```

重点检查：

- 任务目录名应尽量接近中文标题，不应退回 `untitled`
- `audio.wav`
- `transcript.zh.md`
- `notes.md`
- `titles.md`

状态预期：

- 生成指定目标后状态合理更新
- 默认生成时不应误覆盖已有中文 `transcript.zh.md`

4. 局部重生成

任选一个已有任务目录：

```bash
video2post generate TASK_DIR --targets titles
```

重点检查：

- 不重新下载音频
- 不重新转写
- 只更新目标文件

5. 断点续跑

任选一个已有任务目录：

```bash
video2post retry TASK_DIR
video2post retry TASK_DIR --generate --targets titles
```

重点检查：

- YouTube 看 `transcript.en.md`
- B 站看 `transcript.zh.md`
- 不重复跑已经完成的步骤

6. 失败路径

推荐样例：`invalid-url`

```bash
video2post process "https://example.com/video" --output ./outputs-check
```

重点检查：

- `meta.json` 是否落盘
- 平台是否为 `unknown`
- 错误信息是否写入
- 状态是否变成 `failed`

## 建议回归节奏

### 小改动后

- `video2post --help`
- `video2post samples`
- 跑一条相关链路
- 跑对应测试文件

### 跨模块改动后

- 跑一条 YouTube 样例
- 跑一条 B 站样例
- 跑 `generate`
- 跑 `retry`
- 跑失败路径
- 跑相关 `pytest`

### 准备提交前

- 至少跑一次与本次改动最相关的真实样例
- 至少跑一次相关测试文件
- 确认没有把调试产物误加入 git
