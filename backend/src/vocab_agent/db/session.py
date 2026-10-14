"""数据库连接与初始化。

为什么用标准库 sqlite3，而不是 SQLAlchemy：
    表结构小且固定，SQL 直接看得懂、方便审查；也少一个依赖。
    如果以后表多起来，再换 ORM 也不影响上层调用。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..config import get_settings

# schema.sql 和本文件放在同一个目录里
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    """打开数据库连接。

    参数 db_path 不传时用配置里的默认库（backend/data/app.db），
    测试里会传临时路径，这样就互不干扰。
    """
    settings = get_settings()
    path = Path(db_path) if db_path else settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)

    # check_same_thread=False 的原因：
    #   LangGraph 执行节点时会用到线程池，连接会跨线程被使用，
    #   而 sqlite3 默认禁止跨线程（会直接报 ProgrammingError）。
    #   这是单机自用应用，访问量很小；配合 WAL 和 busy_timeout，
    #   偶发的并发写会自动等待而不是报错。
    conn = sqlite3.connect(path, check_same_thread=False)
    # 让查询结果能按列名取值（row["headword"]），比下标好读
    conn.row_factory = sqlite3.Row
    # 打开外键约束（SQLite 默认是关的）
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL 模式：读写不互相阻塞，本地单机也够用
    conn.execute("PRAGMA journal_mode = WAL")
    # 遇到锁时最多等 5 秒，而不是立刻抛 "database is locked"
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """按 schema.sql 建表。已经存在的表不会被改动，可以重复执行。"""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
