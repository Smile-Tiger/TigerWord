"""清洗层：把解析出来的原始记录变成规范词条。

【清洗的边界（重要）】
    只做**无损清洗**，不改写词条本身：
        做：去掉首尾标点、把折行产生的多余空格合掉、把音标拆成英/美两栏
        不做：词形还原、合并重复词条、按难度筛词
    原因见设计方案 6.4.1：用户导入什么就背什么。
"""

from __future__ import annotations

import re

from ..contracts import EntryDraft, RawRecord

# 英式音标：形如 "英:/ˈæpl/"（冒号可能是中文全角）
UK_PHONETIC_PATTERN = re.compile(r"英\s*[:：]\s*(/[^/]+/)")
# 美式音标：形如 "美:/ˈæpl/"
US_PHONETIC_PATTERN = re.compile(r"美\s*[:：]\s*(/[^/]+/)")
# 只有一个音标、没有英美前缀的情况，形如 "/ˈæpl/"
BARE_PHONETIC_PATTERN = re.compile(r"^(/[^/]+/)$")
# 汉字之间的空格（PDF 折行留下的），要删掉："处理危 机的" -> "处理危机的"
CJK_INNER_SPACE_PATTERN = re.compile(r"(?<=[\u4e00-\u9fff])[ \t]+(?=[\u4e00-\u9fff])")


def clean_word(text: str) -> str:
    """清洗单词本身。

    - 压缩空白（折行会留下多余空格："major  in" -> "major in"）
    - 去掉首尾标点。那两条 "takes effect." / "State Council Information Office."
      末尾的句号是用户划词时把句子标点一起划进去的，不是单词的一部分。
    """
    collapsed = re.sub(r"\s+", " ", text.strip())
    return collapsed.strip(".,;:!?、。，；：！？\"'").strip()


def clean_definition(text: str | None) -> str | None:
    """清洗释义：主要就是把折行产生的中文空格合掉。"""
    if not text:
        return None
    collapsed = re.sub(r"\s+", " ", text.strip())
    return CJK_INNER_SPACE_PATTERN.sub("", collapsed) or None


def split_phonetic(raw: str | None) -> tuple[str | None, str | None]:
    """把原始音标文本拆成（英式, 美式）。

    三种情况：
        "英:/a/ 美:/b/"  -> ("/a/", "/b/")      两种都有
        "/a/"            -> ("/a/", "/a/")      只有一种，英美共用
        None / 空        -> (None, None)        没有音标（短语通常是这样）
    """
    if not raw:
        return None, None

    text = raw.strip()
    uk_match = UK_PHONETIC_PATTERN.search(text)
    us_match = US_PHONETIC_PATTERN.search(text)
    uk = uk_match.group(1) if uk_match else None
    us = us_match.group(1) if us_match else None

    # 没写"英/美"前缀、整块就是一个音标时，两栏都填它
    if uk is None and us is None:
        bare = BARE_PHONETIC_PATTERN.match(text)
        if bare:
            return bare.group(1), bare.group(1)

    return uk, us


def to_draft(record: RawRecord, source: str = "parse") -> EntryDraft | None:
    """一条原始记录 -> 一条候选词条。

    返回 None 表示这条记录清洗后是空的（比如整行只有标点），应当跳过。
    """
    word = clean_word(record.raw_word)
    if not word:
        return None

    uk, us = split_phonetic(record.raw_phonetic)
    draft = EntryDraft.from_word(
        word,
        definition=clean_definition(record.raw_definition),
        source=source,  # type: ignore[arg-type]
    )
    draft.phonetic_uk = uk
    draft.phonetic_us = us
    return draft


def to_drafts(records: list[RawRecord]) -> list[EntryDraft]:
    """批量转换，自动丢掉清洗后为空的记录。"""
    drafts: list[EntryDraft] = []
    for record in records:
        draft = to_draft(record)
        if draft is not None:
            drafts.append(draft)
    return drafts
