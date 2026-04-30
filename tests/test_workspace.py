from video2post.writers.workspace import _slugify


def test_slugify_preserves_chinese_characters():
    assert _slugify("川普让美国被羞辱！") == "川普让美国被羞辱"


def test_slugify_still_normalizes_english_titles():
    assert _slugify("Learn 95% of Codex in 30 Minutes!") == "learn-95-of-codex-in-30-minutes"
