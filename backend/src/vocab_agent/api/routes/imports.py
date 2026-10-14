"""导入接口：上传一个文件，跑完整条导入管线，返回导入报告。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ...agent.graph import import_file
from ...config import get_settings
from ..deps import get_db

router = APIRouter(prefix="/api/imports", tags=["imports"])

# 目前支持的输入类型。加 Excel、图片时，这里和 agent/nodes.py 的适配器一起加。
SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".text"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB，够放几千词的导出文件


@router.post("")
async def upload_wordbook(
    file: UploadFile = File(...), conn: sqlite3.Connection = Depends(get_db)
) -> dict:
    """上传生词文件并导入。

    返回导入报告：解析出多少条、新增/更新多少、补全补了几条、有什么提醒。
    """
    # 只取文件名部分，防止有人用 ../../ 这种路径搞事情
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        supported = "、".join(sorted(SUPPORTED_SUFFIXES))
        raise HTTPException(
            status_code=400,
            detail=f"暂时不支持 {suffix or '这种'} 格式，目前支持：{supported}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件是空的")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="文件太大了（上限 20MB）")

    # 先落到上传目录，再交给导入管线（管线内部还会归档一份到 imports/）
    upload_dir = get_settings().data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / filename
    target.write_bytes(content)

    try:
        return import_file(conn, target)
    except ValueError as exc:
        # 比如"不支持的文件类型""文件解析不出内容"，给前端一个清楚的提示
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/history")
def import_history(conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    """最近的导入记录，界面上显示"上次导了什么、进来多少词"。"""
    rows = conn.execute(
        "SELECT * FROM import_batches ORDER BY id DESC LIMIT 20"
    ).fetchall()
    return [dict(row) for row in rows]
