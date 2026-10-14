"""导入流程的状态定义。

LangGraph 里每个节点都接收这个字典，返回"要更新的字段"，
框架负责合并后传给下一个节点。total=False 表示字段可以逐步出现。
"""

from __future__ import annotations

from typing import Any, TypedDict

from ..contracts import EntryDraft, RawRecord


class ImportState(TypedDict, total=False):
    # ---- 输入 ----
    source_path: str        # 用户给的文件的归档路径
    input_kind: str         # pdf | text（以后会有 sheet | image）

    # ---- 解析产物 ----
    raw_records: list[RawRecord]   # 从文件里抠出来的原始记录
    declared_count: int | None     # 页眉声明的词数，用于自校验
    warnings: list[str]            # 解析过程中的异常提示

    # ---- 清洗与补全产物 ----
    drafts: list[EntryDraft]       # 规范后的候选词条
    enrich_report: dict[str, Any]  # 补全统计：补了几条、多少条存疑

    # ---- 结果 ----
    batch_id: int
    report: dict[str, Any]         # 导入报告：新增/更新/未变/补全情况
