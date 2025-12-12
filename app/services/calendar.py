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
    events = []
    user_id = None
    if username:
        cur = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_row = cur.fetchone()
        if user_row:
            user_id = user_row["id"]

    if not user_id:
        # 如果没有用户上下文，则无法查询事件，可以返回空或抛出异常
        return []

    # 1. 查询课程事件 (occurrences)
    sql_courses = """SELECT o.*, c.name as course_name, c.teacher, c.course_code
                     FROM occurrences o JOIN courses c ON o.course_id = c.id
                     WHERE c.user_id = ? AND o.starts_at >= ? AND o.ends_at <= ?"""
    params_courses = [user_id, start_iso, end_iso]
    if season:
        sql_courses += " AND o.season = ?"
        params_courses.append(season)
    sql_courses += " ORDER BY o.starts_at"

    cur_courses = conn.execute(sql_courses, params_courses)
    for r in cur_courses.fetchall():
        r_dict = dict(r)
        events.append({
            "title": r_dict.get("course_name"),
            "periodStart": r_dict.get("period_start"),
            "periodCount": r_dict.get("period_count"),
            "start": r_dict.get("starts_at"),
            "end": r_dict.get("ends_at"),
            "location": r_dict.get("classroom"),
            "teacher": r_dict.get("teacher"),
            "season": r_dict.get("season"),
            "weekday": r_dict.get("weekday"),
            "type": "course"
        })

    # 2. 查询自定义事件 (events)
    sql_events = """SELECT * FROM events
                    WHERE user_id = ? AND start_time >= ? AND end_time <= ?
                    ORDER BY start_time"""
    cur_events = conn.execute(sql_events, [user_id, start_iso, end_iso])
    for r in cur_events.fetchall():
        r_dict = dict(r)
        events.append({
            "title": r_dict.get("title"),
            "start": r_dict.get("start_time"),
            "end": r_dict.get("end_time"),
            "location": r_dict.get("location"),
            "description": r_dict.get("description"),
            "type": "custom"
        })

    # 3. 按开始时间排序合并后的事件
    events.sort(key=lambda x: x["start"])
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