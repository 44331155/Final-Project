from typing import List, Optional
from datetime import datetime
import sqlite3
import hashlib
import uuid

def _iso_to_dt(s: str) -> datetime:
    # 支持 ISO 格式字符串（无时区）
    return datetime.fromisoformat(s)

def _make_uid(event: dict) -> str:
    # 用事件信息生成唯一 UID（稳定且唯一）
    payload = f"{event.get('title','')}-{event.get('start','')}-{event.get('end','')}-{event.get('location','')}"
    h = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"{h}@final-project.local"

def build_events_from_db(conn: sqlite3.Connection, start_iso: str, end_iso: str, season: Optional[str]=None, username: Optional[str]=None) -> List[dict]:
    """
    从数据库读取 occurrences + courses 并格式化为统一事件列表。
    start_iso/end_iso 格式：YYYY-MM-DDTHH:MM:SS
    season: 可选 '春'/'夏'/'秋'/'冬' 进行过滤
    username: 可选，若你的表有 user/owner 字段可据此过滤（当前实现尝试兼容存在与否）
    """
    # 基本查询：按时间范围过滤 starts_at 在区间内的 occurrences
    sql = """SELECT o.*, c.name as course_name, c.teacher, c.course_code
             FROM occurrences o JOIN courses c ON o.course_id = c.id
             WHERE o.starts_at >= ? AND o.ends_at <= ?"""
    params = [start_iso, end_iso]
    if season:
        sql += " AND o.season = ?"
        params.append(season)

    # 如果 occurrences 中存在 owner/username 字段，应当按 username 过滤
    # 这里检查列是否存在再决定是否添加过滤条件
    try:
        cur = conn.execute("PRAGMA table_info(occurrences)")
        cols = [r["name"] for r in cur.fetchall()]
    except Exception:
        cols = []

    if "owner" in cols and username:
        sql += " AND o.owner = ?"
        params.append(username)

    sql += " ORDER BY o.starts_at"

    cur = conn.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]

    events = []
    for r in rows:
        events.append({
            "title": r.get("course_name"),
            "periodStart": r.get("period_start"),
            "periodCount": r.get("period_count"),
            "start": r.get("starts_at"),
            "end": r.get("ends_at"),
            "location": r.get("classroom"),
            "teacher": r.get("teacher"),
            "season": r.get("season"),
            "weekday": r.get("weekday"),
            "type": "course"
        })

    # TODO: 可合并自定义事件表（events）等，当前仅返回课程 events
    return events

def _format_dt_for_ics(dt: datetime) -> str:
    # 输出为 YYYYMMDDTHHMMSS （不含时区后缀），多数日历程序能识别
    return dt.strftime("%Y%m%dT%H%M%S")

def generate_ics(events: List[dict]) -> str:
    """
    根据 events 列表生成简单的 iCalendar 文本
    每个 event dict 需至少包含: title, start (ISO), end (ISO), location, description
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Final-Project//Timetable//EN"
    ]
    now = datetime.utcnow()
    dtstamp = _format_dt_for_ics(now)

    for ev in events:
        try:
            dt_start = _iso_to_dt(ev["start"])
            dt_end = _iso_to_dt(ev["end"])
        except Exception:
            # skip invalid
            continue
        uid = _make_uid(ev)
        lines += [
            "BEGIN:VEVENT",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{_format_dt_for_ics(dt_start)}",
            f"DTEND:{_format_dt_for_ics(dt_end)}",
            f"SUMMARY:{ev.get('title','')}",
            f"LOCATION:{ev.get('location','') or ''}",
            f"DESCRIPTION:{ev.get('description','') or ''}",
            "END:VEVENT"
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)