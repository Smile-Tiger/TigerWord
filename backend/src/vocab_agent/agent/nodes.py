"""导入流程的各个节点。

每个节点只做一件事，重活都交给 ingest/ 和 db/——
这里只负责"把它们按顺序串起来"。这样做的好处是节点很薄，
哪天要换掉 LangGraph，这些逻辑一行都不用改。
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict
from pathlib import Path

from ..config import get_settings
from ..contracts import make_headword
from ..db import repo
from ..ingest import enrich as enrich_module
from ..ingest.normalize import to_drafts
from ..ingest.pdf_parser import parse_pdf
from ..ingest.text_parser import parse_text
from ..llm.config import resolve_llm_config
from .. import runtime_settings as runtime
from .state import ImportState
from .tools import archive_source, file_hash

# 支持的文件类型 -> 用哪个解析通道
PDF_SUFFIXES = {".pdf"}
TEXT_SUFFIXES = {".txt", ".md", ".text", ""}


def detect_input(state: ImportState) -> dict:
    """第 1 站：判断这是什么类型的文件。

    以后支持 Excel、图片，就在这里多加一个分支，
    后面的节点完全不用动（这就是 6.3 输入适配器矩阵的落点）。
    """
    suffix = Path(state["source_path"]).suffix.lower()
    if suffix in PDF_SUFFIXES:
        return {"input_kind": "pdf"}
    if suffix in TEXT_SUFFIXES:
        return {"input_kind": "text"}
    raise ValueError(f"暂时不支持这种文件类型：{suffix or '（没有扩展名）'}")


def extract(state: ImportState) -> dict:
    """第 2 站：按类型选解析通道，把文件还原成一条条原始记录。"""
    path = state["source_path"]
    document = parse_pdf(path) if state["input_kind"] == "pdf" else parse_text(path)
    return {
        "raw_records": document.records,
        "declared_count": document.declared_count,
        "warnings": list(document.warnings),
    }


def normalize_node(state: ImportState) -> dict:
    """第 3 站：无损清洗（去首尾标点、合空格、拆音标），并丢掉空记录。"""
    drafts = to_drafts(state["raw_records"])
    warnings = list(state.get("warnings", []))

    skipped = len(state["raw_records"]) - len(drafts)
    if skipped:
        warnings.append(f"{skipped} 条记录清洗后是空的，已跳过")

    return {"drafts": drafts, "warnings": warnings}


def enrich_node(state: ImportState, conn: sqlite3.Connection) -> dict:
    """第 4 站：补全缺失的音标和释义（缓存 -> 词典 -> LLM）。

    补全失败不会中断导入：补不到的字段就空着，用户照样能背这个词。
    这里从数据库读 LLM 配置，所以用户在前端填的 Key 会优先生效。
    """
    drafts, report = enrich_module.enrich_drafts(
        list(state["drafts"]),
        llm_config=resolve_llm_config(conn),
        enabled=runtime.enrich_enabled(conn),
    )
    return {"drafts": drafts, "enrich_report": asdict(report)}


def persist_node(state: ImportState, conn: sqlite3.Connection) -> dict:
    """第 5 站：入库。

    入库是"合并"不是"追加"：同一个词再次导入不会变成两条，
    已有字段也不会被覆盖（只填空缺）。
    """
    settings = get_settings()
    path = Path(state["source_path"])

    # 原始文件归档一份，以后改清洗规则可以拿它重跑
    archived = archive_source(path, settings.imports_dir) if path.exists() else path
    batch_id = repo.create_batch(
        conn, str(archived), file_hash(path) if path.exists() else "", state["input_kind"]
    )

    counters = {"added": 0, "updated": 0, "unchanged": 0}
    entry_ids: dict[str, int] = {}
    for draft in state["drafts"]:
        status, entry_id = repo.upsert_entry(conn, draft, batch_id)
        counters[status] += 1
        entry_ids[draft.headword] = entry_id

    # 原始记录留档，顺便记下它对应到哪个词条，方便对账
    for record in state["raw_records"]:
        repo.save_raw_record(
            conn, batch_id, record, entry_ids.get(make_headword(record.raw_word))
        )
    conn.commit()

    enrich_report = dict(state.get("enrich_report") or {})
    needs_review = int(enrich_report.get("low_confidence", 0))
    repo.finish_batch(
        conn,
        batch_id,
        total=len(state["drafts"]),
        added=counters["added"],
        updated=counters["updated"],
        unchanged=counters["unchanged"],
        needs_review=needs_review,
    )

    report = {
        "batch_id": batch_id,
        "source": str(archived),
        "input_kind": state["input_kind"],
        "declared_count": state.get("declared_count"),
        "parsed": len(state["raw_records"]),
        "imported": len(state["drafts"]),
        **counters,
        "needs_review": needs_review,
        "enrich": enrich_report,
        "warnings": state.get("warnings", []),
        "entries_in_db": repo.count_entries(conn),
    }
    return {"batch_id": batch_id, "report": report}
