import sqlite3
from pathlib import Path
import argparse
from rich.console import Console
from rich.table import Table

DEFAULT_DB = Path("data/schedule.db")

QUERY_VIEW = """
SELECT id, starts_at, ends_at, week, weekday, period_start, period_count,
       classroom, season, semester, single_week, double_week, note,
       course_name, course_code, teacher, department
FROM v_calendar_events
WHERE 1=1
"""
QUERY_JOIN = """
SELECT o.id, o.starts_at, o.ends_at, o.week, o.weekday, o.period_start, o.period_count,
       o.classroom, o.season, o.semester, o.single_week, o.double_week, o.note,
       c.name AS course_name, c.course_code, c.teacher, c.department
FROM occurrences o
JOIN courses c ON o.course_id = c.id
WHERE 1=1
"""

def build_query(use_view: bool, semester, season, start_from, start_to, limit):
    sql = QUERY_VIEW if use_view else QUERY_JOIN
    params = []
    if semester:
        sql += " AND semester = ?"
        params.append(semester)
    if season:
        sql += " AND season = ?"
        params.append(season)
    if start_from:
        sql += " AND starts_at >= ?"
        params.append(start_from)
    if start_to:
        sql += " AND ends_at <= ?"
        params.append(start_to)
    sql += " ORDER BY starts_at LIMIT ?"
    params.append(limit)
    return sql, params

def main():
    parser = argparse.ArgumentParser(description="可视化课表/日历事件")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite 路径")
    parser.add_argument("--semester", help="学期过滤，例如 2024-2025-1")
    parser.add_argument("--season", help="季节过滤，春/夏/秋/冬")
    parser.add_argument("--from", dest="start_from", help="开始时间下限，ISO 格式，如 2024-09-01T00:00:00")
    parser.add_argument("--to", dest="start_to", help="结束时间上限，ISO 格式，如 2024-12-31T23:59:59")
    parser.add_argument("--limit", type=int, default=500, help="最多显示多少行")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"数据库不存在: {db_path}")
        return

    console = Console()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        # 判断视图是否存在
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='v_calendar_events'")
        use_view = cur.fetchone() is not None

        sql, params = build_query(use_view, args.semester, args.season, args.start_from, args.start_to, args.limit)
        rows = conn.execute(sql, params).fetchall()

    if not rows:
        console.print("[yellow]没有数据[/]")
        return

    table = Table(title="课表 / 日历事件")
    table.add_column("id", style="dim")
    table.add_column("课程", style="cyan")
    table.add_column("教师", style="magenta")
    table.add_column("学期", style="green")
    table.add_column("季节", style="green")
    table.add_column("周", justify="right")
    table.add_column("星期", justify="right")
    table.add_column("节次", justify="right")
    table.add_column("节数", justify="right")
    table.add_column("开始时间", style="white")
    table.add_column("结束时间", style="white")
    table.add_column("教室", style="blue")
    table.add_column("单双周", style="dim")
    table.add_column("备注", style="dim")

    for r in rows:
        table.add_row(
            str(r["id"]),
            r["course_name"],
            r["teacher"],
            r["semester"] or "",
            r["season"] or "",
            str(r["week"]),
            str(r["weekday"]),
            str(r["period_start"]),
            str(r["period_count"]),
            r["starts_at"],
            r["ends_at"],
            r["classroom"],
            ("单" if r["single_week"] else "") + ("双" if r["double_week"] else ""),
            r["note"] or "",
        )

    console.print(table)

if __name__ == "__main__":
    main()