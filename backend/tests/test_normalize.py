"""清洗层测试。

这里断言的是"清洗的边界"：该清的清干净，不该动的绝对不动。
"""

from __future__ import annotations

from vocab_agent.contracts import RawRecord
from vocab_agent.ingest.normalize import (
    clean_definition,
    clean_word,
    split_phonetic,
    to_draft,
    to_drafts,
)


# --------------------------------------------------------------------------
# 单词清洗
# --------------------------------------------------------------------------


def test_去掉首尾标点():
    """用户划词时会把句子末尾的句号一起划进来，那不是单词的一部分。"""
    assert clean_word("takes effect.") == "takes effect"
    assert clean_word("State Council Information Office.") == "State Council Information Office"


def test_压缩多余空格():
    """PDF 折行会在单词中间留下多余空格。"""
    assert clean_word("major  in sth") == "major in sth"
    assert clean_word("  dozens of  ") == "dozens of"


def test_原始大小写保留在_display_里():
    """专用名词的大小写要留住，不能全变小写给用户看。"""
    draft = to_draft(RawRecord(seq_no=1, raw_word="Iran"))
    assert draft is not None
    assert draft.headword == "iran"   # 主键小写，用于去重
    assert draft.display == "Iran"    # 展示保留原样


# --------------------------------------------------------------------------
# 释义清洗
# --------------------------------------------------------------------------


def test_去掉汉字之间的空格():
    """折行造成的"处理危 机的"要合成"处理危机的"。"""
    assert clean_definition("n. 危机的；用于处理危 机的") == "n. 危机的；用于处理危机的"


def test_英文单词之间的空格要保留():
    """只删汉字之间的空格，英文单词之间不能连起来。"""
    assert clean_definition("adj. 租用的 n. [计]专线") == "adj. 租用的 n. [计]专线"


def test_空释义返回_None():
    assert clean_definition(None) is None
    assert clean_definition("   ") is None


# --------------------------------------------------------------------------
# 音标拆分
# --------------------------------------------------------------------------


def test_英美音标都有():
    assert split_phonetic("英:/ˌkɒnsl'teɪʃn/ 美:/ˌkɑːnsl'teɪʃn/") == (
        "/ˌkɒnsl'teɪʃn/",
        "/ˌkɑːnsl'teɪʃn/",
    )


def test_只有一种音标时英美两栏都填它():
    assert split_phonetic("/li:st/") == ("/li:st/", "/li:st/")


def test_没有音标时两栏都为空():
    """短语通常没有音标，比如 "dozens of"。"""
    assert split_phonetic(None) == (None, None)
    assert split_phonetic("") == (None, None)


# --------------------------------------------------------------------------
# 一条记录 -> 一条候选词条
# --------------------------------------------------------------------------


def test_判断单词还是短语():
    word = to_draft(RawRecord(seq_no=1, raw_word="crisis"))
    phrase = to_draft(RawRecord(seq_no=2, raw_word="dozens of"))
    assert word is not None and word.kind == "word"
    assert phrase is not None and phrase.kind == "phrase"


def test_空记录被丢掉():
    """整行只有标点的记录应当跳过，不能变成空词条进库。"""
    assert to_draft(RawRecord(seq_no=1, raw_word="   ")) is None
    assert to_draft(RawRecord(seq_no=2, raw_word="...")) is None


def test_不做词形还原_单复数是两条独立词条():
    """这是产品决定（设计方案 6.4.1）：

    用户导入什么就背什么。soldiers 不会变成 soldier，
    facilities 和 facility 也不会被合并成一条。
    """
    drafts = to_drafts(
        [
            RawRecord(seq_no=1, raw_word="facility"),
            RawRecord(seq_no=2, raw_word="facilities"),
            RawRecord(seq_no=3, raw_word="soldiers"),
        ]
    )
    assert [d.headword for d in drafts] == ["facility", "facilities", "soldiers"]
