from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional, List, Literal
import sqlite3
from ..models.schemas import TimetableRawResp
from .deps import get_current_user
from ..storage.session_store import get_sso
from ..services.timetable import fetch_kblist, TimetableFetchError, parse_kblist_to_occurrences
from ..storage.db import get_conn, init_schema, upsert_course, insert_occurrence, delete_occurrences_by_semester, cleanup_orphan_courses
from ..config import settings

router = APIRouter()

@router.get("", response_model=TimetableRawResp)
async def get_timetable(
    semester: str = Query(..., description="例如 2024-2025-1 或 2024-2025-2"),
    strict: Optional[bool] = Query(True, description="为 false 时不按学期过滤，直接返回全部 kbList"),
    username: str = Depends(get_current_user),
):
    sso_cookie = get_sso(username)
    if not sso_cookie:
        raise HTTPException(status_code=401, detail="登录态已过期，请重新登录")

    try:
        kb_list = await fetch_kblist(sso_cookie, semester_id=semester, strict_filter=bool(strict))
        return {"code": 0, "message": "ok", "data": {"kbList": kb_list}}
    except TimetableFetchError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"未知错误: {e}")

@router.post("/sync")
async def sync_timetable(
    semester: str = Query(...),
    username: str = Depends(get_current_user),
):
    sso_cookie = get_sso(username)
    if not sso_cookie:
        raise HTTPException(status_code=401, detail="登录态已过期，请重新登录")

    try:
        kb_list = await fetch_kblist(sso_cookie, semester_id=semester, strict_filter=True)
    except TimetableFetchError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 将课表数据转化为记录
    occs = parse_kblist_to_occurrences(kb_list) 

    conn = get_conn(settings.DB_PATH)
    init_schema(conn)
    try:
        # 先清空该学期旧数据
        delete_occurrences_by_semester(conn, semester)

        for occ in occs:
            course_id = upsert_course(conn, occ["course_code"], occ["course_name"], occ["teacher"])
            insert_occurrence(conn, {
                "course_id": course_id,
                "week": occ["week"],
                "weekday": occ["weekday"],
                "period_start": occ["period_start"],
                "period_count": occ["period_count"],
                "classroom": occ["classroom"],
                "starts_at": occ["starts_at"],
                "ends_at": occ["ends_at"],
                "single_week": occ["single_week"],
                "double_week": occ["double_week"],
                "season": occ["season"],
                "semester": occ.get("semester"),
                "note": occ["note"],
            })
        # 可选：清理不再引用的课程
        cleanup_orphan_courses(conn)

        conn.commit()
    finally:
        conn.close()

    return {"code": 0, "message": "ok", "data": {"synced": len(occs)}}

@router.get("/by-week")
async def by_week(
    week: int = Query(..., ge=1),
    season: Optional[str] = Query(None, pattern="^(春|夏|秋|冬)$"),
    weekday: Optional[int] = Query(None, ge=1, le=7),
    username: str = Depends(get_current_user),
):
    conn = get_conn(settings.DB_PATH)
    try:
        sql = """SELECT o.*, c.name as course_name, c.teacher, c.course_code
                 FROM occurrences o JOIN courses c ON o.course_id = c.id
                 WHERE o.week = ?"""
        params: List = [week]
        if season:
            sql += " AND o.season = ?"
            params.append(season)
        if weekday:
            sql += " AND o.weekday = ?"
            params.append(weekday)
        sql += " ORDER BY o.weekday, o.period_start"
        cur = conn.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        events = [
            {
                "id": r["id"],
                "weekday": r["weekday"],
                "season": r["season"],
                "title": r["course_name"],
                "teacher": r["teacher"],
                "classroom": r["classroom"],
                "periodStart": r["period_start"],
                "periodCount": r["period_count"],
                "start": r["starts_at"],
                "end": r["ends_at"],
                "courseCode": r["course_code"]
            } for r in rows
        ]
        return {"code": 0, "message": "ok", "data": events}
    finally:
        conn.close()

@router.get("/by-date")
async def by_date(
    date_str: str = Query(..., description="YYYY-MM-DD"),
    season: Optional[str] = Query(None, pattern="^(春|夏|秋|冬)$"),
    username: str = Depends(get_current_user),
):
    conn = get_conn(settings.DB_PATH)
    try:
        start = f"{date_str}T00:00:00"
        end = f"{date_str}T23:59:59"
        sql = """SELECT o.*, c.name as course_name, c.teacher, c.course_code
                 FROM occurrences o JOIN courses c ON o.course_id = c.id
                 WHERE o.starts_at >= ? AND o.ends_at <= ?"""
        params: List = [start, end]
        if season:
            sql += " AND o.season = ?"
            params.append(season)
        sql += " ORDER BY o.starts_at ASC"
        cur = conn.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        events = [
            {
                "id": r["id"],
                "season": r["season"],
                "title": r["course_name"],
                "subtitle": f'{r["teacher"]} · {r["classroom"]}',
                "start": r["starts_at"],
                "end": r["ends_at"],
                "location": r["classroom"],
                "courseCode": r["course_code"]
            } for r in rows
        ]
        return {"code": 0, "message": "ok", "data": events}
    finally:
        conn.close()

@router.get("/template")
async def get_week_template(
    semester: str = Query(..., description="学期标识，例如 2024-2025-1"),
    season_type: int = Query(..., description="前半学期：1（春秋），后半学期：2（冬夏）"),
    week_type_input: int = Query(..., description="周类型：1=单周，2=双周"),
    username: str = Depends(get_current_user),
):
    if semester.endswith("-1"):
        season = "秋" if season_type == 1 else "冬"
    else:
        season = "春" if season_type == 1 else "夏"

    if week_type_input == 1:
        week_type = "single"
    else:
        week_type = "double"
    """
    获取指定学期、季节和周类型的“周课表模板”。
    这个接口会返回一个去重后的、代表一周内所有课程安排的列表。
    """
    conn = get_conn(settings.DB_PATH)
    conn.row_factory = sqlite3.Row  # 确保可以按列名访问
    try:
        # 我们使用 GROUP BY 对课程、星期、节次等关键信息进行分组
        # 这样，一门每周都上的课在模板中只会出现一次
        sql = """
        SELECT
            o.weekday,
            o.period_start,
            o.period_count,
            o.classroom,
            o.season,
            o.single_week,
            o.double_week,
            c.name AS course_name,
            c.teacher,
            c.course_code,
            GROUP_CONCAT(DISTINCT o.week) AS weeks_raw
        FROM occurrences o
        JOIN courses c ON o.course_id = c.id
        WHERE o.semester = ? AND o.season = ?
        """
        params: List = [semester, season]

        if week_type == "single":
            sql += " AND o.double_week = 0"
        elif week_type == "double":
            sql += " AND o.single_week = 0"
        # 如果 week_type 是 'all'，则不添加额外筛选条件

        sql += """
        GROUP BY
            c.id, o.weekday, o.period_start, o.period_count, o.classroom, o.season, o.single_week, o.double_week
        ORDER BY
            o.weekday, o.period_start;
        """

        cur = conn.execute(sql, params)
        rows = cur.fetchall()

        # 将查询结果格式化为更友好的 JSON
        template_events = [
            {
                "weekday": r["weekday"],
                "periodStart": r["period_start"],
                "periodCount": r["period_count"],
                "title": r["course_name"],
                "teacher": r["teacher"],
                "classroom": r["classroom"],
                "weekType": "single" if r["single_week"] else ("double" if r["double_week"] else "all"),
            } for r in rows
        ]

        return {"code": 0, "message": "ok", "data": template_events}
    except Exception as e:
        # 可以在这里添加更详细的日志记录
        raise HTTPException(status_code=500, detail=f"生成课表模板时出错: {e}")
    finally:
        conn.close()