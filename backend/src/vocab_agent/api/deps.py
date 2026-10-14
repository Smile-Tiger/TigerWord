"""接口层的公共依赖。

数据库连接用 FastAPI 的依赖注入：每个请求开一个连接，请求结束就关掉。
SQLite 连接不能跨线程复用，这样做最省心。
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from ..db.session import connect, init_db


def get_db() -> Iterator[sqlite3.Connection]:
    """给每个请求一个数据库连接。

    第一次调用时顺带建表（init_db 是幂等的，建过的表不会动）。
    """
    conn = connect()
    init_db(conn)
    try:
        yield conn
    finally:
        conn.close()
