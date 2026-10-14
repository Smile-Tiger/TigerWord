"""PDF 解析器测试。

样例文件是 tests/fixtures/make_fixture.py 生成的"版式复刻件"，
它把真实文件里最容易出错的几种排版情况都造了出来。
下面每条断言都对应一个真实踩过的坑，注释里写明了为什么这么测。
"""

from __future__ import annotations

import re

import pytest

from conftest import REAL_EXPORTS, SAMPLE_PDF
from vocab_agent.ingest.pdf_parser import parse_pdf

# 页脚形如 "1 of 6"
FOOTER_PATTERN = re.compile(r"\d+\s+of\s+\d+")


@pytest.fixture(scope="module")
def doc():
    """整个模块只解析一次，避免重复读文件。"""
    return parse_pdf(SAMPLE_PDF)


def test_条数与页眉声明一致(doc):
    """页眉写着"共 6 词"，就应该正好解析出 6 条，并且不产生警告。"""
    assert doc.declared_count == 6
    assert len(doc.records) == 6
    assert doc.warnings == []


def test_序号连续不缺行(doc):
    """序号必须连续。早期版本因为表头过滤的位置判断不对，丢过 5 条。"""
    assert [r.seq_no for r in doc.records] == [1, 2, 3, 4, 5, 6]


def test_英美音标都被还原(doc):
    """英式音标画在序号行上方、美式画在下方，两块都要归位到同一个词条。"""
    first = doc.records[0]
    assert first.raw_word == "consultation"
    assert first.raw_phonetic == "英:/ˌkɒnsl'teɪʃn/ 美:/ˌkɑːnsl'teɪʃn/"
    assert first.raw_definition == "n. 磋商(会议),咨询,专家会诊"


def test_没有音标的词条不会把邻行的音标吸过来(doc):
    """第 3 条 militaries 既没音标也没释义。

    这是最容易串行的一条：它上面一条的释义、下面一条的音标都在附近。
    如果解析器按文本流读，这里必然出错。
    """
    third = doc.records[2]
    assert third.raw_word == "militaries"
    assert third.raw_phonetic is None
    assert third.raw_definition is None


def test_折行的释义被拼回完整一行(doc):
    """释义折成两行（第一行压在序号行上方、第二行在下方）时要拼回一条。"""
    crisis = doc.records[1]
    assert crisis.raw_definition.startswith("n. 危机；决定性时刻")
    assert crisis.raw_definition.endswith("机的")


def test_只有一种音标时也能收下(doc):
    """real 文件里有不少词只有一个音标（没有"英/美"前缀）。"""
    leased = doc.records[3]
    assert leased.raw_phonetic == "/li:st/"


def test_页脚不会粘到最后一个词条(doc):
    """页脚 "1 of 1" 被拆成多个碎片，只靠文本匹配过滤不干净，
    必须按页面底部的坐标整条丢掉。"""
    for record in doc.records:
        blob = " ".join(
            filter(None, [record.raw_word, record.raw_phonetic, record.raw_definition])
        )
        assert not FOOTER_PATTERN.search(blob), f"第 {record.seq_no} 条被页脚污染：{blob}"


@pytest.mark.skipif(
    not REAL_EXPORTS,
    reason="没有真实导出文件。把你的 PDF 放到 backend/tests/fixtures/ 就会自动启用这个测试",
)
def test_真实导出文件也能完整解析():
    """对真实文件做同样的校验：条数必须和页眉声明的一致。"""
    for path in REAL_EXPORTS:
        parsed = parse_pdf(path)
        assert parsed.records, f"{path.name} 一条都没解析出来"
        assert parsed.declared_count == len(parsed.records), (
            f"{path.name} 声明 {parsed.declared_count} 条，实际解析 {len(parsed.records)} 条"
        )
