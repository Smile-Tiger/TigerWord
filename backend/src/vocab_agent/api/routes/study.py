"""学习接口：取今天该背什么、提交一次作答。"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ...db import repo
from ...srs import scheduler
from ..deps import get_db
from ..schemas import AnswerIn, AnswerOut, EntryOut, TodayQueueOut

router = APIRouter(prefix="/api/study", tags=["study"])


def _to_entry(row: sqlite3.Row, *, with_state: bool) -> EntryOut:
    """数据库行 -> 接口模型。

    学习接口会把复习状态一起带上（前端要显示"这是第几轮"），
    别的地方只要词条本身，所以用 with_state 控制。
    """
    keys = set(row.keys())
    return EntryOut(
        id=row["id"],
        display=row["display"],
        kind=row["kind"],
        phonetic_uk=row["phonetic_uk"],
        phonetic_us=row["phonetic_us"],
        definition=row["definition"],
        stage=row["stage"] if with_state and "stage" in keys else None,
        step=row["step"] if with_state and "step" in keys else None,
        due_at=row["due_at"] if with_state and "due_at" in keys else None,
    )


@router.get("/today", response_model=TodayQueueOut)
def read_today(conn: sqlite3.Connection = Depends(get_db)) -> TodayQueueOut:
    """今天的队列：要新学的词 + 到期的复习词。

    新词数量按"每日新词配额"来（界面上可以改）。
    """
    queue = scheduler.build_today_queue(conn)
    return TodayQueueOut(
        new=[_to_entry(row, with_state=True) for row in queue["new"]],
        review=[_to_entry(row, with_state=True) for row in queue["review"]],
        daily_new_limit=repo.get_daily_new_limit(conn, 20),
    )


@router.post("/answer", response_model=AnswerOut)
def submit_answer(
    payload: AnswerIn, conn: sqlite3.Connection = Depends(get_db)
) -> AnswerOut:
    """提交一次作答，返回这个词的新状态和本场剩余卡片数。

    rating 三种取值：
        known    认识   -> 升级
        fuzzy    模糊   -> 不升级，明天再见
        unknown  不认识 -> 降级回炉
    """
    try:
        result = scheduler.record_review(
            conn, entry_id=payload.entry_id, rating=payload.rating, mode=payload.mode
        )
    except ValueError as exc:
        # 词条不存在时给出清楚的 404，而不是 500
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # 本场还剩多少张卡。答对的词当天不再出现，答错的会留在队列里。
    queue = scheduler.build_today_queue(conn)
    remaining = len(queue["review"]) + len(queue["new"])
    if result["again_today"]:
        remaining += 1  # 这个词稍后还要再出现一次

    return AnswerOut(
        stage=result["stage"],
        step=result["step"],
        due_at=result["due_at"],
        again_today=result["again_today"],
        remaining=remaining,
    )
