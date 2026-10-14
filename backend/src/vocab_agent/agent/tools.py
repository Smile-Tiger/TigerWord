"""导入流程会用到的小工具函数。

单独放一处的目的：这些操作以后可能会被别的入口复用
（比如命令行、接口层、以后的图片导入），不该埋在某个节点里。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..db import repo


def file_hash(path: str | Path) -> str:
    """算文件的指纹（SHA-256 前 16 位）。

    用途：判断"这个文件是不是之前导过"。
    同一份文件重复导入时，界面上可以提醒用户，避免反复背同样的词。
    """
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def archive_source(path: str | Path, imports_dir: Path) -> Path:
    """把用户上传的原始文件复制一份归档，方便以后回溯。

    原始文件是"事实来源"：清洗规则改了可以拿它重跑，
    所以导入完成后不依赖用户再传一次。
    """
    source = Path(path)
    imports_dir.mkdir(parents=True, exist_ok=True)
    target = imports_dir / source.name
    if not target.exists():
        target.write_bytes(source.read_bytes())
    return target


def summarise_batch(conn, batch_id: int) -> dict:
    """读回一条导入批次的统计信息，给接口层和命令行用。"""
    row = conn.execute(
        "SELECT * FROM import_batches WHERE id = ?", (batch_id,)
    ).fetchone()
    if row is None:
        return {}
    return {
        "batch_id": row["id"],
        "source": row["source"],
        "input_kind": row["input_kind"],
        "total": row["total"],
        "added": row["added"],
        "updated": row["updated"],
        "unchanged": row["unchanged"],
        "needs_review": row["needs_review"],
        "entries_in_db": repo.count_entries(conn),
    }
