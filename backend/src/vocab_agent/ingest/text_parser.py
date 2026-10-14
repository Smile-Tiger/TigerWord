"""纯文本解析器：处理"粘贴一份单词列表"这种输入。

支持的格式很简单，因为用户手打的列表通常也就这几种：
    1. 一行一个单词
         apple
         banana
    2. 制表符分隔（从 Excel 复制粘贴过来最常见）
         apple    /ˈæpl/    n. 苹果

    "两个字段挤在一列"（如 apple /ˈæpl/ n. 苹果 全在一行）
    这种情况的切分留给 AI 处理（见 6.7.2），这里只做最保守的拆列：
    有制表符就按制表符拆，没有就把整行当成单词，
    宁可少拆，也不要把用户的一个短语拆坏。
"""

from __future__ import annotations

from pathlib import Path

from ..contracts import RawRecord
from .base import ParsedDocument


def parse_text(source: str | Path) -> ParsedDocument:
    """解析纯文本。source 可以是文件路径，也可以直接是粘贴的文本内容。"""
    raw_text = _read_source(source)
    records: list[RawRecord] = []

    for line_no, line in enumerate(raw_text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue  # 空行直接跳过

        cells = [cell.strip() for cell in stripped.split("\t")]
        records.append(
            RawRecord(
                seq_no=line_no,
                raw_word=cells[0],
                raw_phonetic=cells[1] if len(cells) > 1 and cells[1] else None,
                # 第三列往后都算释义（有的列表释义里自己带制表符）
                raw_definition=" ".join(c for c in cells[2:] if c) or None
                if len(cells) > 2
                else None,
            )
        )

    return ParsedDocument(records=records, input_kind="text")


def _read_source(source: str | Path) -> str:
    """判断传进来的是文件路径还是文本内容。

    规则：指向一个确实存在的文件，就按文件读；否则当成文本内容本身。
    这样接口层可以直接把粘贴的文本丢进来，不用先落盘。
    """
    path = Path(source)
    if len(str(source)) < 260 and path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    return str(source)
