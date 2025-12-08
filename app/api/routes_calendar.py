from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import Response, JSONResponse
from typing import Optional, List
from datetime import datetime, timedelta
import sqlite3
import json

from ..api.deps import get_current_user
from ..config import settings
from ..services.calendar import build_events_from_db, generate_ics

router = APIRouter()


@router.get("/events")
async def get_calendar_events(
    date_from: str = Query(..., description="YYYY-MM-DD"),
    date_to: str = Query(..., description="YYYY-MM-DD"),
    season: Optional[str] = Query(None, description="可选：春/夏/秋/冬"),
    username: str = Depends(get_current_user),
):
    """
    返回指定日期区间内的日历事件（课程 + 自定义事件）
    返回结构：{ code, message, data: [ {title,start,end,location,description,type} ] }
    """
    # 基本日期校验
    try:
        dt_from = datetime.fromisoformat(date_from)
        dt_to = datetime.fromisoformat(date_to)
    except Exception:
        raise HTTPException(status_code=400, detail="date_from/date_to 格式应为 YYYY-MM-DD")
    # normalize to full-day range
    start = f"{date_from}T00:00:00"
    end = f"{date_to}T23:59:59"

    try:
        conn = sqlite3.connect(settings.DB_PATH)
        conn.row_factory = sqlite3.Row
        events = build_events_from_db(conn, start, end, season=season, username=username)
        return JSONResponse({"code": 0, "message": "ok", "data": events})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询日历失败: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.get("/export.ics")
async def export_ics(
    week: Optional[int] = Query(None, description="按教学周导出（优先于 date_from/date_to）"),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    season: Optional[str] = Query(None, description="可选：春/夏/秋/冬"),
    username: str = Depends(get_current_user),
):
    """
    导出 ICS 文件。
    优先参数：week -> 按周导出；否则使用 date_from/date_to 导出区间。
    """
    try:
        conn = sqlite3.connect(settings.DB_PATH)
        conn.row_factory = sqlite3.Row

        if week is not None:
            # 按 week 查询当周（使用学期默认 CURRENT_TERM）
            # 这里按 week 查询 occurrences 表
            sql = """SELECT o.*, c.name AS course_name, c.teacher, c.course_code
                     FROM occurrences o JOIN courses c ON o.course_id = c.id
                     WHERE o.week = ?"""
            params = [week]
            if season:
                sql += " AND o.season = ?"
                params.append(season)
            sql += " ORDER BY o.starts_at"
            cur = conn.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
            events = []
            for r in rows:
                events.append({
                    "id": r["id"],
                    "title": r["course_name"],
                    "start": r["starts_at"],
                    "end": r["ends_at"],
                    "location": r["classroom"],
                    "description": f"教师: {r['teacher']} 课程代码: {r.get('course_code','')}",
                    "type": "course",
                    "season": r.get("season")
                })
        else:
            if not date_from or not date_to:
                raise HTTPException(status_code=400, detail="请提供 week 或 date_from 和 date_to")
            start = f"{date_from}T00:00:00"
            end = f"{date_to}T23:59:59"
            events = build_events_from_db(conn, start, end, season=season, username=username)

        ics_text = generate_ics(events)
        return Response(content=ics_text, media_type="text/calendar")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出 ICS 失败: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass