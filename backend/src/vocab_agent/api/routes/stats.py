"""统计接口：词库进度、正确率、最近的导入记录。"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from ...db import repo
from ..deps import get_db

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
def read_stats(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """看板要用的数据，一次取回来，避免前端发一堆请求。"""
    by_stage = repo.count_by_stage(conn)

    # 正确率：只统计复习阶段的作答，学习阶段第一次见面的对错意义不大
    accuracy_row = conn.execute(
        """
        SELECT
            SUM(CASE WHEN rating = 'known' THEN 1 ELSE 0 END) AS known,
            COUNT(*) AS total
          FROM review_logs
        """
    ).fetchone()
    known = int(accuracy_row["known"] or 0)
    total_answers = int(accuracy_row["total"] or 0)

    recent_batches = [
        dict(row)
        for row in conn.execute(
            "SELECT * FROM import_batches ORDER BY id DESC LIMIT 5"
        ).fetchall()
    ]

    return {
        "entries_total": repo.count_entries(conn),
        "by_stage": {
            "new": by_stage.get("new", 0),
            "learning": by_stage.get("learning", 0),
            "review": by_stage.get("review", 0),
            "graduated": by_stage.get("graduated", 0),
        },
        "answers_total": total_answers,
        "accuracy": round(known / total_answers, 3) if total_answers else None,
        "recent_batches": recent_batches,
    }
