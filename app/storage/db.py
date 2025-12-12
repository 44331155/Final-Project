import sqlite3
from pathlib import Path
from typing import Dict

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_encrypted TEXT NOT NULL -- 将 password_hash 修改为 password_encrypted
);

CREATE TABLE IF NOT EXISTS courses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  course_code TEXT NOT NULL,
  name TEXT NOT NULL,
  teacher TEXT NOT NULL,
  department TEXT,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_courses_code_teacher ON courses (user_id, course_code, teacher);

CREATE TABLE IF NOT EXISTS occurrences (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  course_id INTEGER NOT NULL,
  week INTEGER NOT NULL,
  weekday INTEGER NOT NULL,
  period_start INTEGER NOT NULL,
  period_count INTEGER NOT NULL,
  classroom TEXT NOT NULL,
  starts_at TEXT NOT NULL,
  ends_at TEXT NOT NULL,
  single_week INTEGER DEFAULT 0,
  double_week INTEGER DEFAULT 0,
  season TEXT NOT NULL,  -- 新增季节标签：春/夏/秋/冬
  semester TEXT, -- 学期标识，例如 2024-2025-1
  note TEXT,
  FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_occurrences_time ON occurrences (starts_at, ends_at);
CREATE INDEX IF NOT EXISTS idx_occurrences_week_day ON occurrences (week, weekday);
CREATE INDEX IF NOT EXISTS idx_occurrences_season ON occurrences (season);
CREATE INDEX IF NOT EXISTS idx_occurrences_semester ON occurrences (semester);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  start_time TEXT NOT NULL,
  end_time TEXT NOT NULL,
  location TEXT,
  description TEXT,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_events_time ON events (start_time, end_time);

CREATE VIEW IF NOT EXISTS v_calendar_events AS
SELECT
  o.id,
  o.starts_at,
  o.ends_at,
  o.week,
  o.weekday,
  o.period_start,
  o.period_count,
  o.classroom,
  o.season,
  o.semester,
  o.single_week,
  o.double_week,
  o.note,
  c.name       AS course_name,
  c.course_code,
  c.teacher,
  c.department
FROM occurrences o
JOIN courses c ON o.course_id = c.id;
"""

def get_conn(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_schema(conn: sqlite3.Connection):
    conn.executescript(SCHEMA_SQL)

def upsert_course(conn: sqlite3.Connection, user_id: int, course_code: str, name: str, teacher: str, department=None) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO courses(user_id, course_code, name, teacher, department) VALUES (?, ?, ?, ?, ?)",
        (user_id, course_code, name, teacher, department)
    )
    cur = conn.execute(
        "SELECT id FROM courses WHERE user_id=? AND course_code=? AND teacher=?",
        (user_id, course_code, teacher)
    )
    row = cur.fetchone()
    return int(row["id"])

def insert_occurrence(conn: sqlite3.Connection, occ: Dict):
    conn.execute(
        """INSERT INTO occurrences
           (course_id, week, weekday, period_start, period_count, classroom, starts_at, ends_at, single_week, double_week, season, semester, note)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (occ["course_id"], occ["week"], occ["weekday"], occ["period_start"], occ["period_count"], occ["classroom"],
         occ["starts_at"], occ["ends_at"], int(occ.get("single_week", 0)), int(occ.get("double_week", 0)), occ["season"], occ.get("semester"), occ.get("note"))
    )

def delete_occurrences_by_semester(conn: sqlite3.Connection, user_id: int, semester: str):
    conn.execute("""
        DELETE FROM occurrences
        WHERE semester = ? AND course_id IN (
            SELECT id FROM courses WHERE user_id = ?
        )
    """, (semester, user_id))

def cleanup_orphan_courses(conn: sqlite3.Connection):
    conn.execute("DELETE FROM courses WHERE id NOT IN (SELECT DISTINCT course_id FROM occurrences)")