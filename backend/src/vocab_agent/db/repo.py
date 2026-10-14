"""数据访问层：所有读写数据库的操作都收在这里。

上层（导入管线、接口层）不直接写 SQL，
这样以后换表结构或加索引，只需要改这一个文件。
"""

from __future__ import annotations

import sqlite3

from ..contracts import EntryDraft, RawRecord
from ..utils import now_iso


# ---------------------------------------------------------------------------
# 导入批次
# ---------------------------------------------------------------------------


def create_batch(
    conn: sqlite3.Connection, source: str, file_hash: str, input_kind: str
) -> int:
    """新建一条导入批次记录，返回批次 id。

    每导入一个文件就记一条，方便以后回答"这批词是什么时候、从哪个文件来的"。
    """
    cur = conn.execute(
        """
        INSERT INTO import_batches (source, file_hash, input_kind, imported_at)
        VALUES (?, ?, ?, ?)
        """,
        (source, file_hash, input_kind, now_iso()),
    )
    conn.commit()
    return int(cur.lastrowid)


def finish_batch(
    conn: sqlite3.Connection,
    batch_id: int,
    *,
    total: int,
    added: int,
    updated: int,
    unchanged: int,
    needs_review: int,
) -> None:
    """导入结束后回填统计结果（文件里有多少条、新增多少、更新多少、多少条待复核）。"""
    conn.execute(
        """
        UPDATE import_batches
           SET total = ?, added = ?, updated = ?, unchanged = ?, needs_review = ?
         WHERE id = ?
        """,
        (total, added, updated, unchanged, needs_review, batch_id),
    )
    conn.commit()


def find_previous_batch(conn: sqlite3.Connection, file_hash: str) -> sqlite3.Row | None:
    """按文件指纹找之前的导入记录。

    用途：同一个文件重复导入时，界面上可以提示"这个文件上次已经导过了"。
    """
    return conn.execute(
        "SELECT * FROM import_batches WHERE file_hash = ? ORDER BY id DESC LIMIT 1",
        (file_hash,),
    ).fetchone()


# ---------------------------------------------------------------------------
# 原始记录留档
# ---------------------------------------------------------------------------


def save_raw_record(
    conn: sqlite3.Connection, batch_id: int, record: RawRecord, entry_id: int | None = None
) -> None:
    """把文件里的原貌存一份。

    为什么存：清洗规则以后可能会调整。有了原貌，
    任何时候都能拿原始数据重新跑一遍，不需要用户再导一次文件。
    """
    conn.execute(
        """
        INSERT INTO raw_entries (batch_id, seq_no, raw_word, raw_phonetic, raw_definition, entry_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            batch_id,
            record.seq_no,
            record.raw_word,
            record.raw_phonetic,
            record.raw_definition,
            entry_id,
        ),
    )


# ---------------------------------------------------------------------------
# 词条入库（合并，不是追加）
# ---------------------------------------------------------------------------


def upsert_entry(
    conn: sqlite3.Connection, draft: EntryDraft, batch_id: int
) -> tuple[str, int]:
    """把一个候选词条写进库，返回 (状态, 词条 id)。

    状态有三种：
        added     库裡原来没有这个词，新建
        updated   词已经有了，但这次补上了新的字段
        unchanged 词已经有了，且没有任何变化

    合并规则（重要，和"用户导入什么就背什么"配套）：
        - 已有的字段**不覆盖**，只填空缺的
        - 唯一的例外：旧的释义是 AI 猜的（source='ai'），
          这次文件里带了真实释义（source='parse'），则以文件为准
          —— 因为 AI 补的算不上"用户的数据"，文件里的才是
    """
    existing = conn.execute(
        "SELECT * FROM entries WHERE headword = ?", (draft.headword,)
    ).fetchone()
    stamp = now_iso()

    if existing is None:
        cur = conn.execute(
            """
            INSERT INTO entries (
                headword, display, kind, phonetic_uk, phonetic_us, definition,
                source, confidence, first_batch_id, last_seen_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                draft.headword,
                draft.display,
                draft.kind,
                draft.phonetic_uk,
                draft.phonetic_us,
                draft.definition,
                draft.source,
                draft.confidence,
                batch_id,
                stamp,
                stamp,
            ),
        )
        entry_id = int(cur.lastrowid)
        # 新词同时建一条复习状态，stage='new' 表示"还没学过"
        conn.execute(
            "INSERT INTO srs_state (entry_id, stage, step) VALUES (?, 'new', 0)",
            (entry_id,),
        )
        conn.commit()
        return "added", entry_id

    # ---- 已有词条：只填空缺字段 ----
    updates: dict[str, object] = {}
    prefer_file = existing["source"] == "ai" and draft.source == "parse"

    for field in ("phonetic_uk", "phonetic_us", "definition"):
        new_value = getattr(draft, field)
        if not new_value:
            continue  # 新数据这块是空的，没什么可写
        old_value = existing[field]
        if not old_value or prefer_file:
            if old_value != new_value:
                updates[field] = new_value

    # 无论有没有字段变化，都记一次"最近见到它的时间"
    updates["last_seen_at"] = stamp
    set_clause = ", ".join(f"{name} = ?" for name in updates)
    conn.execute(
        f"UPDATE entries SET {set_clause} WHERE id = ?",
        (*updates.values(), existing["id"]),
    )
    conn.commit()

    changed = len(updates) > 1  # 只有 last_seen_at 变化不算"更新"
    return ("updated" if changed else "unchanged"), int(existing["id"])


# ---------------------------------------------------------------------------
# 查询与设置
# ---------------------------------------------------------------------------


def count_entries(conn: sqlite3.Connection) -> int:
    """词库里一共有多少条词。"""
    return int(conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0])


def count_by_stage(conn: sqlite3.Connection) -> dict[str, int]:
    """按学习阶段统计条数，看板用。"""
    rows = conn.execute(
        "SELECT stage, COUNT(*) AS n FROM srs_state GROUP BY stage"
    ).fetchall()
    return {row["stage"]: int(row["n"]) for row in rows}


def get_setting(conn: sqlite3.Connection, key: str) -> str | None:
    """读一个设置项，没有就返回 None。"""
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    """写一个设置项（存在就覆盖）。"""
    conn.execute(
        """
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )
    conn.commit()


def get_daily_new_limit(conn: sqlite3.Connection, default: int) -> int:
    """每日新词配额：优先用用户改过的值，没改过就用配置里的默认值。"""
    raw = get_setting(conn, "daily_new_limit")
    if raw is None:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default
