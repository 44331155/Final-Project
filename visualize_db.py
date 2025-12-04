import sqlite3
from pathlib import Path
from rich.console import Console
from rich.table import Table

# --- 配置 ---
# 数据库文件路径，请确保与您的设置一致
DB_PATH = "data/schedule.db"
# --- 配置结束 ---

def visualize_data(db_path: str):
    """
    连接到数据库并以表格形式打印课表数据。
    """
    db_file = Path(db_path)
    if not db_file.exists():
        print(f"错误: 数据库文件未找到: {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # SQL 查询，连接 courses 和 occurrences 表
        sql = """
        SELECT 
            c.name as course_name,
            c.teacher,
            o.week,
            o.weekday,
            o.period_start,
            o.period_count,
            o.classroom,
            o.season,
            o.starts_at,
            o.ends_at
        FROM occurrences o
        JOIN courses c ON o.course_id = c.id
        ORDER BY o.starts_at, o.week, o.weekday, o.period_start;
        """
        
        cur = conn.execute(sql)
        rows = cur.fetchall()

        if not rows:
            print("数据库中没有找到课表数据。")
            return

        # 使用 rich 创建表格
        table = Table(title="课表数据可视化")
        table.add_column("课程名称", justify="left", style="cyan", no_wrap=True)
        table.add_column("教师", style="magenta")
        table.add_column("周", justify="right", style="green")
        table.add_column("星期", justify="right", style="green")
        table.add_column("开始节", justify="right", style="green")
        table.add_column("节数", justify="right", style="green")
        table.add_column("季节", style="yellow")
        table.add_column("教室", style="blue")
        table.add_column("开始时间", style="white")
        table.add_column("结束时间", style="white")

        for row in rows:
            table.add_row(
                row["course_name"],
                row["teacher"],
                str(row["week"]),
                str(row["weekday"]),
                str(row["period_start"]),
                str(row["period_count"]),
                row["season"],
                row["classroom"],
                row["starts_at"],
                row["ends_at"],
            )

        console = Console()
        console.print(table)

    except sqlite3.Error as e:
        print(f"数据库错误: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    visualize_data(DB_PATH)