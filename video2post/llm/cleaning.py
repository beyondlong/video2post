import re


def clean_llm_output(text: str) -> str:
    without_thinking = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return without_thinking.strip()
