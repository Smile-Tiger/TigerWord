"""pytest 公共配置与公共 fixture。"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"

# 版式复刻的样例文件（由 fixtures/make_fixture.py 生成）
SAMPLE_PDF = FIXTURE_DIR / "sample_wordbook.pdf"

# 用户如果把自己的真实导出文件放进 fixtures 目录，下面的测试会自动启用它
REAL_EXPORTS = sorted(FIXTURE_DIR.glob("所有生词本*.pdf"))


@pytest.fixture()
def conn(tmp_path):
    """给每个测试一个干净的临时数据库，测试之间互不影响。

    注意用的是 tmp_path（pytest 提供的临时目录），
    所以跑测试不会碰到你真实的数据（backend/data/app.db）。
    """
    from vocab_agent.db.session import connect, init_db

    connection = connect(tmp_path / "test.db")
    init_db(connection)
    try:
        yield connection
    finally:
        connection.close()
