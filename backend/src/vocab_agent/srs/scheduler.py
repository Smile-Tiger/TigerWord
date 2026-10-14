"""每日队列组装 + 作答落库。

队列公式（设计方案 7.4）：
    今日队列 = min(每日新词配额, 还没学过的词) + 所有到期的复习词

复习量不设上限——到期的就该复习，拖下去只会越滚越多。
"""

from __future__ import annotations

import sqlite3

from ..config import get_settings
from ..db import repo
from ..utils import now_iso, today_str
from .engine import next_state
from .ladder import STAGE_LEARNING


def build_today_queue(
    conn: sqlite3.Connection, daily_new_limit: int | None = None
) -> dict[str, list[sqlite3.Row]]:
    """组装今天的背诵队列。

    返回两个列表：
        review  到期的复习词（也包含今天正在学、还没过关的词）
        new     今天要新学的词，数量受每日配额限制
    """
    if daily_new_limit is None:
        daily_new_limit = repo.get_daily_new_limit(conn, get_settings().daily_new_limit)

    today = today_str()

    # 到期的复习词：状态是 learning 或 review，且到期日已到（或本来就是今天）
    # learning 阶段的 due_at 就是今天，所以会被这里选出来 —— 这就是"当天双轮"的实现方式
    review_rows = conn.execute(
        """
        SELECT e.*, s.stage, s.step, s.due_at, s.correct_streak, s.lapses
          FROM entries e
          JOIN srs_state s ON s.entry_id = e.id
         WHERE s.stage IN ('learning', 'review')
           AND (s.due_at IS NULL OR s.due_at <= ?)
         ORDER BY s.due_at ASC, s.step ASC, e.id ASC
        """,
        (today,),
    ).fetchall()

    # 新词：按入库顺序取，数量受每日配额限制
    new_rows = conn.execute(
        """
        SELECT e.*, s.stage, s.step, s.due_at, s.correct_streak, s.lapses
          FROM entries e
          JOIN srs_state s ON s.entry_id = e.id
         WHERE s.stage = 'new'
         ORDER BY e.id ASC
         LIMIT ?
        """,
        (daily_new_limit,),
    ).fetchall()

    return {"review": list(review_rows), "new": list(new_rows)}


def record_review(
    conn: sqlite3.Connection,
    *,
    entry_id: int,
    rating: str,
    mode: str,
    session_id: int | None = None,
) -> dict:
    """记录一次作答：更新复习状态 + 写一条流水。

    返回更新后的状态，前端用它判断"这个词本场还要不要再出现一次"。
    """
    row = conn.execute(
        "SELECT * FROM srs_state WHERE entry_id = ?", (entry_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"词条 {entry_id} 没有复习状态，数据库可能不完整")

    result = next_state(
        stage=row["stage"],
        step=row["step"],
        correct_streak=row["correct_streak"],
        lapses=row["lapses"],
        rating=rating,
    )
    stamp = now_iso()

    conn.execute(
        """
        UPDATE srs_state
           SET stage = ?, step = ?, due_at = ?, correct_streak = ?, lapses = ?,
               total_reviews = total_reviews + 1, last_review_at = ?
         WHERE entry_id = ?
        """,
        (
            result.stage,
            result.step,
            result.due_at,
            result.correct_streak,
            result.lapses,
            stamp,
            entry_id,
        ),
    )
    conn.execute(
        """
        INSERT INTO review_logs (
            entry_id, session_id, rating, mode,
            prev_stage, next_stage, prev_step, next_step, reviewed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry_id,
            session_id,
            rating,
            mode,
            row["stage"],
            result.stage,
            row["step"],
            result.step,
            stamp,
        ),
    )
    conn.commit()

    return {
        "stage": result.stage,
        "step": result.step,
        "due_at": result.due_at,
        # 本场还要不要再出现一次：只有 learning 阶段是这种情况
        "again_today": result.stage == STAGE_LEARNING,
    }
