from fastapi import APIRouter, Depends, HTTPException, Query
from ..models.schemas import EventReq, CommonResp
from typing import List, Optional
from .deps import get_current_user
from ..storage.db import get_conn
from ..config import settings
import sqlite3

router = APIRouter()

def get_user_id(conn: sqlite3.Connection, username: str) -> int:
    cur = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_row = cur.fetchone()
    if not user_row:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user_row["id"]

@router.post("", response_model=CommonResp)
async def add_event(req: EventReq, username: str = Depends(get_current_user)):
    conn = get_conn(settings.DB_PATH)
    try:
        user_id = get_user_id(conn, username)
        conn.execute(
            "INSERT INTO events (user_id, title, start_time, end_time, location) VALUES (?, ?, ?, ?, ?)",
            (user_id, req.title, req.startTime, req.endTime, req.place)
        )
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建事件失败: {e}")
    finally:
        conn.close()
    return {"code": 0, "message": "ok"}

# 改进：使用查询参数进行过滤，而不是请求体
@router.get("", response_model=CommonResp)
async def list_events(
    username: str = Depends(get_current_user),
    start: Optional[str] = None, # 例如: 2025-12-01T00:00:00
    end: Optional[str] = None,   # 例如: 2025-12-31T23:59:59
):
    conn = get_conn(settings.DB_PATH)
    # 关键修复：确保返回的行是类似字典的对象
    conn.row_factory = sqlite3.Row
    try:
        user_id = get_user_id(conn, username)
        
        sql = "SELECT * FROM events WHERE user_id = ?"
        params = [user_id]
        
        if start:
            sql += " AND start_time >= ?"
            params.append(start)
        if end:
            sql += " AND end_time <= ?"
            params.append(end)
            
        sql += " ORDER BY start_time"
        
        cur = conn.execute(sql, params)
        # 现在 dict(row) 可以正常工作了
        events = [dict(row) for row in cur.fetchall()]
        
    except Exception as e:
        # 增加日志打印，方便调试
        print(f"Error in list_events: {e}")
        raise HTTPException(status_code=500, detail=f"获取事件列表失败: {e}")
    finally:
        conn.close()
    return CommonResp(code=0, message="ok", data=events)

@router.get("/{event_id}", response_model=CommonResp)
async def get_event_by_id(event_id: int, username: str = Depends(get_current_user)):
    """
    获取单个事件的详情
    """
    conn = get_conn(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        user_id = get_user_id(conn, username)
        cur = conn.execute(
            "SELECT * FROM events WHERE id = ? AND user_id = ?",
            (event_id, user_id)
        )
        event = cur.fetchone()
        if not event:
            raise HTTPException(status_code=404, detail="事件不存在或无权查看")
        
        return CommonResp(code=0, message="ok", data=dict(event))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取事件失败: {e}")
    finally:
        conn.close()


# 改进：使用路径参数 {event_id} 来定位资源
@router.delete("/{event_id}", response_model=CommonResp)
async def delete_event(event_id: int, username: str = Depends(get_current_user)):
    conn = get_conn(settings.DB_PATH)
    try:
        user_id = get_user_id(conn, username)
        cur = conn.execute(
            "DELETE FROM events WHERE id = ? AND user_id = ?",
            (event_id, user_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="事件不存在或无权操作")
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除事件失败: {e}")
    finally:
        conn.close()
    return {"code": 0, "message": "ok"}

# 改进：使用路径参数 {event_id} 来定位资源
@router.put("/{event_id}", response_model=CommonResp)
async def update_event(
    event_id: int,
    req: EventReq,
    username: str = Depends(get_current_user)
):
    conn = get_conn(settings.DB_PATH)
    try:
        user_id = get_user_id(conn, username)
        cur = conn.execute(
            "UPDATE events SET title = ?, start_time = ?, end_time = ?, location = ? "
            "WHERE id = ? AND user_id = ?",
            (req.title, req.startTime, req.endTime, req.place, event_id, user_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="事件不存在或无权操作")
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新事件失败: {e}")
    finally:
        conn.close()
    return {"code": 0, "message": "ok"}

