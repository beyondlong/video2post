from video2post.llm.cleaning import clean_llm_output


def test_clean_llm_output_removes_multiline_think_block():
    raw = "<think>\nreasoning\nmore reasoning\n</think>\n\n正式内容"

    assert clean_llm_output(raw) == "正式内容"


def test_clean_llm_output_removes_inline_think_block():
    raw = "<think>reasoning</think>ok"

    assert clean_llm_output(raw) == "ok"


def test_clean_llm_output_preserves_text_without_think_block():
    raw = "普通内容\n\n第二段"

    assert clean_llm_output(raw) == raw
