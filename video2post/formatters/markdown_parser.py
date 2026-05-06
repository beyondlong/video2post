import re

from video2post.formatters.models import MarkdownBlock, MarkdownDocument


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_ORDERED_RE = re.compile(r"^\d+[.)]\s+(.*)$")
_TABLE_SEPARATOR_RE = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$")


def parse_markdown(content: str) -> MarkdownDocument:
    lines = content.splitlines()
    blocks: list[MarkdownBlock] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue

        if _is_table_start(lines, index):
            headers = _split_table_row(lines[index])
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and _looks_like_table_row(lines[index].strip()):
                rows.append(_split_table_row(lines[index]))
                index += 1
            blocks.append(MarkdownBlock(kind="table", headers=headers, rows=rows))
            continue

        if stripped.startswith("```"):
            language = stripped[3:].strip() or None
            index += 1
            code_lines: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            blocks.append(
                MarkdownBlock(kind="code_block", text="\n".join(code_lines), language=language)
            )
            continue

        if stripped in {"---", "***", "___"}:
            blocks.append(MarkdownBlock(kind="horizontal_rule"))
            index += 1
            continue

        heading_match = _HEADING_RE.match(stripped)
        if heading_match:
            blocks.append(
                MarkdownBlock(
                    kind="heading",
                    text=heading_match.group(2).strip(),
                    level=len(heading_match.group(1)),
                )
            )
            index += 1
            continue

        if stripped.startswith(">"):
            quote_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote_lines.append(lines[index].strip()[1:].strip())
                index += 1
            blocks.append(MarkdownBlock(kind="blockquote", text="\n".join(quote_lines)))
            continue

        if stripped.startswith(("- ", "* ")):
            items: list[str] = []
            while index < len(lines):
                item = lines[index].strip()
                if not item.startswith(("- ", "* ")):
                    break
                items.append(item[2:].strip())
                index += 1
            blocks.append(MarkdownBlock(kind="unordered_list", items=items))
            continue

        ordered_match = _ORDERED_RE.match(stripped)
        if ordered_match:
            items = []
            while index < len(lines):
                item_match = _ORDERED_RE.match(lines[index].strip())
                if not item_match:
                    break
                items.append(item_match.group(1).strip())
                index += 1
            blocks.append(MarkdownBlock(kind="ordered_list", items=items))
            continue

        paragraph_lines = [line.strip()]
        index += 1
        while index < len(lines):
            next_line = lines[index]
            next_stripped = next_line.strip()
            if not next_stripped or _starts_block(lines, index):
                break
            paragraph_lines.append(next_stripped)
            index += 1
        blocks.append(MarkdownBlock(kind="paragraph", text=" ".join(paragraph_lines)))

    return MarkdownDocument(blocks=blocks)


def _starts_block(lines: list[str], index: int) -> bool:
    stripped = lines[index].strip()
    return bool(
        _is_table_start(lines, index)
        or stripped.startswith("```")
        or stripped in {"---", "***", "___"}
        or _HEADING_RE.match(stripped)
        or stripped.startswith(">")
        or stripped.startswith(("- ", "* "))
        or _ORDERED_RE.match(stripped)
    )


def _is_table_start(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    return _looks_like_table_row(lines[index].strip()) and bool(
        _TABLE_SEPARATOR_RE.match(lines[index + 1].strip())
    )


def _looks_like_table_row(stripped: str) -> bool:
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]
