"""运行时可调设置：用户在界面上能改的那些。

和 .env 的关系：
    .env 是"默认值"，界面里改过的值存在数据库，优先使用。
    这样开发者可以设一套默认值，用户又能自己调。
"""

from __future__ import annotations

import sqlite3

from .config import get_settings
from .db import repo

KEY_DAILY_NEW_LIMIT = "daily_new_limit"
KEY_ENRICH_ENABLED = "enrich_enabled"


def daily_new_limit(conn: sqlite3.Connection) -> int:
    """每日新词配额。界面改过就用界面的，否则用 .env 的默认值。"""
    return repo.get_daily_new_limit(conn, get_settings().daily_new_limit)


def set_daily_new_limit(conn: sqlite3.Connection, value: int) -> None:
    repo.set_setting(conn, KEY_DAILY_NEW_LIMIT, str(max(0, int(value))))


def enrich_enabled(conn: sqlite3.Connection) -> bool:
    """要不要做 AI 补全。用户可以在界面上关掉它。"""
    raw = repo.get_setting(conn, KEY_ENRICH_ENABLED)
    if raw is None:
        return get_settings().enrich_enabled
    return raw.strip().lower() in ("1", "true", "yes", "on")


def set_enrich_enabled(conn: sqlite3.Connection, value: bool) -> None:
    repo.set_setting(conn, KEY_ENRICH_ENABLED, "true" if value else "false")
