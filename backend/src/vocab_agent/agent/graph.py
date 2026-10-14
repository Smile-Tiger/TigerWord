"""把各节点装配成一张状态图（LangGraph）。

流程（对应设计方案 6.6）：

    detect_input -> extract -> normalize -> enrich -> persist

以后要插入"人工确认"这一站，只需在 enrich 和 persist 之间加一个节点，
其它部分不用动。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from . import nodes
from .state import ImportState


def build_graph(conn: sqlite3.Connection):
    """装配导入流程。

    每次导入都新建一张图，并把数据库连接通过闭包传给 persist 节点——
    这样节点函数本身不用关心连接是从哪来的，测试时换成临时库就行。
    """
    builder = StateGraph(ImportState)

    builder.add_node("detect_input", nodes.detect_input)
    builder.add_node("extract", nodes.extract)
    builder.add_node("normalize", nodes.normalize_node)
    # enrich 和 persist 都要用数据库（一个读 LLM 配置，一个写词条），
    # 用闭包把连接传进去，节点函数本身就不用关心连接从哪来
    builder.add_node("enrich", lambda state: nodes.enrich_node(state, conn))
    builder.add_node("persist", lambda state: nodes.persist_node(state, conn))

    builder.add_edge(START, "detect_input")
    builder.add_edge("detect_input", "extract")
    builder.add_edge("extract", "normalize")
    builder.add_edge("normalize", "enrich")
    builder.add_edge("enrich", "persist")
    builder.add_edge("persist", END)

    return builder.compile()


def import_file(conn: sqlite3.Connection, path: str | Path) -> dict:
    """跑完一次完整导入，返回导入报告。

    报告里包含：解析出多少条、新增多少、更新多少、补全补了几条、
    有多少条标了低置信需要人工看一眼。
    """
    graph = build_graph(conn)
    final_state = graph.invoke({"source_path": str(path), "warnings": []})
    return dict(final_state.get("report") or {})
