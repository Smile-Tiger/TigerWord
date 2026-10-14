"""跨层共用的数据结构（也叫"入库契约"）。

EntryDraft 是整条导入链路的收口：
    不管词是从 PDF、表格、图片还是粘贴的文本来的，
    最终都必须变成一个 EntryDraft 才允许进数据库。
所以它放在最顶层，db / ingest / agent 都从这里引用，
避免各层互相 import 造成循环依赖。
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, field_validator

# 词条类型：单个单词 或 短语
Kind = Literal["word", "phrase"]
# 数据来源：解析器抠出来的 / AI 补出来的 / 用户手填的
Source = Literal["parse", "ai", "user"]
# 置信度：AI 补的内容如果是猜的，标 low，让导入页高亮出来
Confidence = Literal["high", "medium", "low"]


def make_headword(text: str) -> str:
    """把一段文本变成去重用的主键。

    规则（只做无损处理，不改写单词本身）：
        1. 去掉首尾空白和首尾标点（"takes effect." -> "takes effect"）
        2. 转小写（"Iran" 和 "iran" 视为同一个词）
        3. 中间连续空格压成一个（"major  in" -> "major in"）

    注意：这里**不做**词形还原。soldiers 就是 soldiers，
    不会变成 soldier —— 这是产品决定（用户导入什么就背什么）。
    """
    cleaned = text.strip().strip(".,;:!?、。，；：！？\"'`()（）[]【】")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.lower()


class RawRecord(BaseModel):
    """解析器直接从文件里抠出来的一条记录，还没清洗。

    它的作用是留档：万一以后清洗规则改了，可以拿原始记录重跑一遍。
    """

    seq_no: int                                   # 文件里的序号
    raw_word: str                                 # 原样单词，未清洗
    raw_phonetic: str | None = None               # 原样音标，可能含"英:/.../ 美:/.../"
    raw_definition: str | None = None             # 原样释义


class EntryDraft(BaseModel):
    """一条候选词条。通过校验后才能写进 entries 表。"""

    headword: str          # 去重主键，由 make_headword 生成
    display: str           # 展示用，保留原始大小写
    kind: Kind             # word | phrase
    phonetic_uk: str | None = None   # 英式音标
    phonetic_us: str | None = None   # 美式音标
    definition: str | None = None    # 中文释义
    source: Source = "parse"         # 这条数据哪来的
    confidence: Confidence | None = None

    @field_validator("headword")
    @classmethod
    def _headword_not_empty(cls, value: str) -> str:
        """主键不能是空的，否则这条数据没有意义，直接判为非法。"""
        if not value or not value.strip():
            raise ValueError("headword 不能为空")
        return value

    @classmethod
    def from_word(
        cls,
        word: str,
        *,
        phonetic_raw: str | None = None,
        definition: str | None = None,
        source: Source = "parse",
    ) -> "EntryDraft":
        """从"一个词 + 可选音标 + 可选释义"造一条候选词条。

        这是最常用的入口：解析器、AI 补全、手填都走它。
        """
        display = re.sub(r"\s+", " ", word.strip().rstrip(".").strip())
        return cls(
            headword=make_headword(word),
            display=display,
            kind="phrase" if " " in display else "word",
            definition=definition,
            source=source,
        )
