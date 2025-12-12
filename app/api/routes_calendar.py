from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import Response
from typing import Optional

# 导入 get_conn 和 CommonResp
from ..storage.db import get_conn
from ..models.schemas import CommonResp
from ..api.deps import get_current_user
from ..services.calendar import build_events_from_db, generate_ics
import sqlite3

router = APIRouter()


# 1. 路径简化为 /calendar, 参数名与 events API 统一
# 2. 使用 response_model 保持一致性
# 3. 使用 Depends(get_conn) 管理数据库连接
@router.get("", response_model=CommonResp)
async def get_calendar_events(
    start: str = Query(..., description="开始时间 (YYYY-MM-DDTHH:MM:SS)"),
    end: str = Query(..., description="结束时间 (YYYY-MM-DDTHH:MM:SS)"),
    season: Optional[str] = Query(None, description="可选：春/夏/秋/冬"),
    username: str = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
):
    """
    返回指定日期区间内的日历事件（课程 + 自定义事件）
    """
    try:
        # 3. 直接将参数传递给服务层，不再手动拼接
        events = build_events_from_db(conn, start, end, season=season, username=username)
        return CommonResp(code=0, message="ok", data=events)
    except Exception as e:
        # 打印错误方便调试
        print(f"Error in get_calendar_events: {e}")
        raise HTTPException(status_code=500, detail=f"查询日历失败: {e}")


# 4. 简化 export.ics 逻辑，复用 build_events_from_db
@router.get("/export.ics")
async def export_ics(
    start: str = Query(..., description="开始时间 (YYYY-MM-DDTHH:MM:SS)"),
    end: str = Query(..., description="结束时间 (YYYY-MM-DDTHH:MM:SS)"),
    season: Optional[str] = Query(None, description="可选：春/夏/秋/冬"),
    username: str = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_conn),
):
    """
    在指定时间范围内导出 ICS 文件。
    """
    try:
        # 关键修改：完全复用 build_events_from_db 函数，不再重复写 SQL
        events = build_events_from_db(conn, start, end, season=season, username=username)
        
        ics_text = generate_ics(events)
        return Response(content=ics_text, media_type="text/calendar")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in export_ics: {e}")
        raise HTTPException(status_code=500, detail=f"导出 ICS 失败: {e}")
