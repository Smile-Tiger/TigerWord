"""命令行入口：不开前端也能先把词导进来、看看今天该背什么。

用法（在 backend 目录下执行）：
    python -m vocab_agent.cli import tests/fixtures/sample_wordbook.pdf
    python -m vocab_agent.cli today
    python -m vocab_agent.cli stats

如果提示找不到模块，先执行一次 pip install -e . ，
或者用 scripts/dev.ps1 里封装好的命令。
"""

from __future__ import annotations

import argparse
import sys

from .agent.graph import import_file
from .db import repo
from .db.session import connect, init_db
from .srs import scheduler


def cmd_import(args: argparse.Namespace) -> int:
    """导入一个文件，并把导入报告打印出来。"""
    conn = connect()
    init_db(conn)

    report = import_file(conn, args.path)
    enrich = report.get("enrich") or {}

    print("导入完成")
    print(f"  文件解析出     ：{report.get('parsed', 0)} 条")
    print(f"  实际入库       ：{report.get('imported', 0)} 条")
    print(f"  新增 / 更新 / 未变：{report.get('added', 0)} / {report.get('updated', 0)} / {report.get('unchanged', 0)}")
    print(f"  补上音标       ：{enrich.get('filled_phonetic', 0)} 条")
    print(f"  补上释义       ：{enrich.get('filled_definition', 0)} 条")
    print(f"  词库总量       ：{report.get('entries_in_db', 0)} 条")

    for note in report.get("warnings") or []:
        print(f"  提醒：{note}")
    for note in enrich.get("notes") or []:
        print(f"  提醒：{note}")
    return 0


def cmd_today(args: argparse.Namespace) -> int:
    """看看今天该背哪些词。"""
    conn = connect()
    init_db(conn)

    queue = scheduler.build_today_queue(conn, daily_new_limit=args.limit)
    print(f"今天：新词 {len(queue['new'])} 个，复习 {len(queue['review'])} 个")
    for row in queue["new"]:
        print(f"  [新] {row['display']}  {row['definition'] or '（暂无释义）'}")
    for row in queue["review"]:
        print(f"  [复] {row['display']}  {row['definition'] or '（暂无释义）'}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """看词库整体情况。"""
    conn = connect()
    init_db(conn)

    print(f"词库总量：{repo.count_entries(conn)} 条")
    for stage, count in sorted(repo.count_by_stage(conn).items()):
        print(f"  {stage:10} {count}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vocab", description="TigerWord 命令行工具")
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="导入一个生词文件")
    p_import.add_argument("path", help="文件路径（PDF 或 txt）")
    p_import.set_defaults(func=cmd_import)

    p_today = sub.add_parser("today", help="查看今天该背的词")
    p_today.add_argument("--limit", type=int, default=None, help="每日新词量（不填用设置里的值）")
    p_today.set_defaults(func=cmd_today)

    p_stats = sub.add_parser("stats", help="查看词库统计")
    p_stats.set_defaults(func=cmd_stats)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except FileNotFoundError as exc:
        print(f"找不到文件：{exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"处理失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
