"""PDF 解析器：把每日英语听力导出的生词本还原成一条条记录。

【为什么不能用普通的文本抽取】
    导出的版式是四列表格：序号 | 单词 | 音标 | 解释。
    但音标那两行的位置很特殊——英式音标在序号行的**上面**，
    美式音标在序号行的**下面**：

        英:/ˌkɒnsl'teɪʃn/
        1  consultation   n. 磋商(会议),咨询,专家会诊
        美:/ˌkɑːnsl'teɪʃn/

    如果按从上到下的顺序读文本，音标就会串到相邻的词条上去。
    所以必须按**坐标**分列：先按 x 判断每个碎片属于哪一列，
    再按 y 把同一列里的碎片拼回完整文字。

【踩过的两个坑（写在这里，免得以后改代码时踩回去）】
    坑 1：页脚 "1 of 6" 被拆成三个独立的词（"1"、"of"、"6"），
          只靠文本匹配过滤不干净，结果页脚粘在每页最后一条词的释义后面，
          变成 "n. pl.当局, 官方 4 of 6"。
          正确做法：按页面底部的 y 坐标整条丢弃。
    坑 2：第 2 页开始的表头位置比第 1 页更高（第 1 页多了标题行），
          用固定 y 阈值过滤表头，会误删每页的第一条记录。
          早期版本因此丢了 5 条（29 / 60 / 88 / 118 / 149）。
          正确做法：按文本内容识别表头，而不是按位置。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber

from ..contracts import RawRecord
from .base import ParsedDocument

# --------------------------------------------------------------------------
# 版式参数（单位：pt。A4 页面宽 595.9，高 841.9）
# 这些数字是量出来的列边界，改版式时只需要调这里。
# --------------------------------------------------------------------------
NO_COL_MAX_X = 72.0        # 序号列：x 右边界
WORD_COL_MAX_X = 200.0     # 单词列：x 右边界
PHONETIC_COL_MAX_X = 335.0  # 音标列：x 右边界（超过它的算释义列）

LINE_TOLERANCE = 2.5       # 纵向差小于这个值，认为是同一个视觉行
RECORD_TOP_PADDING = 7.0   # 记录块向上外扩：英式音标在序号行上方约 5pt
FOOTER_MARGIN = 40.0       # 距页面底部 40pt 以内，视为页脚区域

# 表头文字。第 2 页起表头位置不同，所以按内容识别最稳（坑 2）
HEADER_TOKENS = {"单词", "音标", "解释", "No.", "No"}
# 首页标题行，如 "#所有生词本"、"(共174词)"、"日期："
TITLE_PATTERN = re.compile(r"^#|^\(共\d+词\)$|^日期：?$")
# 页脚，如 "1 of 6"（如果被渲染成一个词，这个正则能兜住）
FOOTER_PATTERN = re.compile(r"^\d+\s*of\s*\d+$")
# 从标题行里读出"共 174 词"，用于校验解析条数
DECLARED_COUNT_PATTERN = re.compile(r"共\s*(\d+)\s*词")


def parse_pdf(path: str | Path) -> ParsedDocument:
    """解析一个 PDF，返回全部记录 + 页眉声明的词数。"""
    records: list[RawRecord] = []
    warnings: list[str] = []
    declared: int | None = None

    with pdfplumber.open(path) as pdf:
        for page_index, page in enumerate(pdf.pages):
            if page_index == 0:
                declared = _read_declared_count(page)
            words = _keep_data_words(page)
            records.extend(_parse_page(words, page_index + 1, warnings))

    # 自校验：解析条数和页眉声明不一致，说明版式可能变了，值得提醒用户
    if declared is not None and declared != len(records):
        warnings.append(
            f"页眉声明 {declared} 条，实际解析出 {len(records)} 条，请人工确认"
        )

    return ParsedDocument(
        records=records,
        declared_count=declared,
        input_kind="pdf",
        warnings=warnings,
    )


def _read_declared_count(page: Any) -> int | None:
    """从首页文字里读出"共 N 词"。读不到就返回 None（不报错）。"""
    text = page.extract_text() or ""
    match = DECLARED_COUNT_PATTERN.search(text)
    return int(match.group(1)) if match else None


def _keep_data_words(page: Any) -> list[dict]:
    """过滤掉表头、标题、页脚，只留下真正的数据碎片。"""
    footer_line = page.height - FOOTER_MARGIN
    kept: list[dict] = []

    for word in page.extract_words():
        text = word["text"]
        if text in HEADER_TOKENS:          # 表头：单词 / 音标 / 解释 / No.
            continue
        if TITLE_PATTERN.match(text):      # 标题行
            continue
        if FOOTER_PATTERN.match(text):     # 页脚（单块渲染时）
            continue
        if word["top"] >= footer_line:     # 页脚（被拆成多块时，见坑 1）
            continue
        kept.append(word)

    return kept


def _parse_page(words: list[dict], page_no: int, warnings: list[str]) -> list[RawRecord]:
    """解析单页。

    思路：以"序号列的纯数字"为锚点切分记录块。
    每个块的范围是「本序号往上 7pt」到「下一个序号往上 7pt」，
    往上外扩是为了接住伏在序号行上方的英式音标。
    """
    anchors = sorted(
        (w for w in words if w["x1"] <= NO_COL_MAX_X and w["text"].isdigit()),
        key=lambda w: w["top"],
    )
    if not anchors:
        warnings.append(f"第 {page_no} 页没有识别到任何序号，可能是空页或版式不同")
        return []

    records: list[RawRecord] = []
    for index, anchor in enumerate(anchors):
        block_top = anchor["top"] - RECORD_TOP_PADDING
        block_bottom = (
            anchors[index + 1]["top"] - RECORD_TOP_PADDING
            if index + 1 < len(anchors)
            else float("inf")
        )
        band = [w for w in words if block_top <= w["top"] < block_bottom]

        # 按 x 分列，再按 y 聚行、按 x 拼字
        word_col = [w for w in band if NO_COL_MAX_X < w["x1"] <= WORD_COL_MAX_X]
        phonetic_col = [w for w in band if WORD_COL_MAX_X < w["x0"] < PHONETIC_COL_MAX_X]
        definition_col = [w for w in band if w["x0"] >= PHONETIC_COL_MAX_X]

        records.append(
            RawRecord(
                seq_no=int(anchor["text"]),
                raw_word=" ".join(_cluster_lines(word_col)).strip(),
                raw_phonetic=" ".join(_cluster_lines(phonetic_col)).strip() or None,
                raw_definition=" ".join(_cluster_lines(definition_col)).strip() or None,
            )
        )

    return records


def _cluster_lines(words: list[dict], tolerance: float = LINE_TOLERANCE) -> list[str]:
    """把同一列里的碎片按纵向位置聚成"视觉行"，再按横向位置拼成文字。

    为什么要先按 y 聚：同一个视觉行里，中文字符和英文字符的基线不一样，
    pdfplumber 给出的 top 值会差零点几到几 pt。先按容差归到同一行，
    再按 x 从左到右拼接，才能还原出正确的阅读顺序。
    """
    if not words:
        return []

    rows: list[dict] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows and abs(word["top"] - rows[-1]["top"]) <= tolerance:
            rows[-1]["words"].append(word)
        else:
            rows.append({"top": word["top"], "words": [word]})

    return [
        " ".join(t["text"] for t in sorted(row["words"], key=lambda w: w["x0"]))
        for row in rows
    ]
