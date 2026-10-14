"""通用小工具。目前只有时间格式化，集中放一处避免各模块各写一套。"""

from __future__ import annotations

from datetime import date, datetime


def now_iso() -> str:
    """当前时间，精确到秒，形如 2026-10-14 21:03:11。

    存字符串而不是时间戳，是为了用 sqlite 命令行直接看库时能读懂。
    """
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def today_str() -> str:
    """今天的日期，形如 2026-10-14。复习到期判断用它做比较。"""
    return date.today().isoformat()
