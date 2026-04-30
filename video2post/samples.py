from dataclasses import dataclass


@dataclass(frozen=True)
class SampleCase:
    name: str
    category: str
    purpose: str
    url: str
    notes: str


SAMPLE_CASES: tuple[SampleCase, ...] = (
    SampleCase(
        name="youtube-short-tech",
        category="youtube",
        purpose="短 YouTube 英文技术视频主链路验收",
        url="https://www.youtube.com/watch?v=474wZZHoWN4",
        notes="用于验证元数据、音频下载、英文转写、中文生成链路。",
    ),
    SampleCase(
        name="youtube-long-tech",
        category="youtube",
        purpose="长 YouTube 英文技术视频分块链路验收",
        url="https://www.youtube.com/watch?v=474wZZHoWN4",
        notes="当前可复用同一真实样例验证长链路代码路径，后续可替换为更长样例。",
    ),
    SampleCase(
        name="bilibili-short-cn",
        category="bilibili",
        purpose="B 站中文视频最小链路验收",
        url="https://www.bilibili.com/video/BV1fA9mBPEZt?t=7.0",
        notes="已验证下载、音频标准化、中文转写、notes 和 titles 生成。",
    ),
    SampleCase(
        name="bilibili-second-cn",
        category="bilibili",
        purpose="B 站中文视频第二条真实验收样例",
        url="https://www.bilibili.com/video/BV1A99yBYEZd?t=9.6",
        notes="用于验证中文链路和 FunASR 实验性 provider 的真实环境表现。",
    ),
    SampleCase(
        name="invalid-url",
        category="negative",
        purpose="无效链接失败路径验收",
        url="https://example.com/video",
        notes="用于验证平台识别、错误记录和失败状态写入。",
    ),
)


def iter_sample_lines() -> list[str]:
    return [
        f"{sample.name} | category={sample.category} | purpose={sample.purpose} | url={sample.url}"
        for sample in SAMPLE_CASES
    ]
