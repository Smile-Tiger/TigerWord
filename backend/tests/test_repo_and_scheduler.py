"""入库合并规则 + 每日队列 + 作答落库 的集成测试。

这些测试回答的是产品问题：
    - 同一个文件重复导入，会不会把词背重复了？
    - AI 补的释义会不会盖掉用户文件里的真释义？
    - 今天该背什么，是怎么算出来的？
"""

from __future__ import annotations

import pytest

from vocab_agent.contracts import EntryDraft
from vocab_agent.db import repo
from vocab_agent.srs import scheduler
from vocab_agent.srs.ladder import RATING_KNOWN, RATING_UNKNOWN, STAGE_LEARNING, STAGE_REVIEW
from vocab_agent.utils import today_str


@pytest.fixture()
def batch_id(conn) -> int:
    """先建一条导入批次，词条都要挂在某个批次上。"""
    return repo.create_batch(conn, "sample.pdf", "hash-of-sample", "pdf")


def make_draft(word: str, definition: str | None = None, source: str = "parse") -> EntryDraft:
    return EntryDraft.from_word(word, definition=definition, source=source)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# 入库：合并而不是追加
# --------------------------------------------------------------------------


def test_新词入库_同时建立学习状态(conn, batch_id):
    status, entry_id = repo.upsert_entry(conn, make_draft("crisis", "n. 危机"), batch_id)

    assert status == "added"
    assert repo.count_entries(conn) == 1

    state = conn.execute(
        "SELECT * FROM srs_state WHERE entry_id = ?", (entry_id,)
    ).fetchone()
    assert state["stage"] == "new"   # 新词默认"还没学过"


def test_同一个文件重复导入不会产生重复词条(conn, batch_id):
    repo.upsert_entry(conn, make_draft("crisis", "n. 危机"), batch_id)
    status, _ = repo.upsert_entry(conn, make_draft("crisis", "n. 危机"), batch_id)

    assert status == "unchanged"
    assert repo.count_entries(conn) == 1


def test_只填空缺字段_不覆盖已有内容(conn, batch_id):
    """第一次进来只有单词，第二次进来带了释义 —— 应该把释义补上。"""
    repo.upsert_entry(conn, make_draft("crisis"), batch_id)
    status, entry_id = repo.upsert_entry(conn, make_draft("crisis", "n. 危机"), batch_id)

    assert status == "updated"
    row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
    assert row["definition"] == "n. 危机"


def test_文件里的真释义会覆盖_AI_猜的释义(conn, batch_id):
    """AI 补的算不上"用户的数据"。

    所以当用户后来导入了带真释义的文件时，以文件为准。
    """
    repo.upsert_entry(conn, make_draft("crisis", "AI 猜的释义", source="ai"), batch_id)
    status, entry_id = repo.upsert_entry(
        conn, make_draft("crisis", "n. 危机", source="parse"), batch_id
    )

    assert status == "updated"
    row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
    assert row["definition"] == "n. 危机"
    assert row["source"] == "ai"  # source 记录的是这个词条最早怎么来的，不跟着改


def test_AI_释义不会覆盖文件里的真释义(conn, batch_id):
    """反过来要拦住：文件里的真释义不能被 AI 的结果盖掉。"""
    repo.upsert_entry(conn, make_draft("crisis", "n. 危机", source="parse"), batch_id)
    status, entry_id = repo.upsert_entry(
        conn, make_draft("crisis", "AI 猜的释义", source="ai"), batch_id
    )

    assert status == "unchanged"
    row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
    assert row["definition"] == "n. 危机"


# --------------------------------------------------------------------------
# 每日队列
# --------------------------------------------------------------------------


def test_新词按每日配额进队列(conn, batch_id):
    for word in ("crisis", "sign", "dialogue", "tariff"):
        repo.upsert_entry(conn, make_draft(word, "n. 测试"), batch_id)

    queue = scheduler.build_today_queue(conn, daily_new_limit=2)
    assert len(queue["new"]) == 2       # 只放配额内的
    assert queue["review"] == []        # 还没人到期


def test_配额可以在设置里改(conn, batch_id):
    for word in ("crisis", "sign", "dialogue"):
        repo.upsert_entry(conn, make_draft(word, "n. 测试"), batch_id)

    repo.set_setting(conn, "daily_new_limit", "1")
    queue = scheduler.build_today_queue(conn)
    assert len(queue["new"]) == 1


def test_答对之后当天不再出现_明天才复习(conn, batch_id):
    _, entry_id = repo.upsert_entry(conn, make_draft("crisis", "n. 危机"), batch_id)

    result = scheduler.record_review(
        conn, entry_id=entry_id, rating=RATING_KNOWN, mode="choice"
    )
    assert result["stage"] == STAGE_REVIEW
    assert result["again_today"] is False

    queue = scheduler.build_today_queue(conn)
    assert queue["new"] == []       # 已经不是新词
    assert queue["review"] == []    # 到期日是明天，今天不该出现


def test_答错之后当天还要再背一次(conn, batch_id):
    _, entry_id = repo.upsert_entry(conn, make_draft("crisis", "n. 危机"), batch_id)

    result = scheduler.record_review(
        conn, entry_id=entry_id, rating=RATING_UNKNOWN, mode="self_report"
    )
    assert result["stage"] == STAGE_LEARNING
    assert result["again_today"] is True

    # learning 阶段到期日就是今天，所以会被复习队列再次选出来
    queue = scheduler.build_today_queue(conn)
    assert [row["id"] for row in queue["review"]] == [entry_id]


def test_每次作答都留下流水(conn, batch_id):
    _, entry_id = repo.upsert_entry(conn, make_draft("crisis", "n. 危机"), batch_id)
    scheduler.record_review(conn, entry_id=entry_id, rating=RATING_KNOWN, mode="choice")

    log = conn.execute("SELECT * FROM review_logs WHERE entry_id = ?", (entry_id,)).fetchone()
    assert log["rating"] == RATING_KNOWN
    assert log["prev_stage"] == "new"       # 作答前
    assert log["next_stage"] == STAGE_REVIEW  # 作答后
    assert log["reviewed_at"].startswith(today_str()[:7])  # 记的是本月
