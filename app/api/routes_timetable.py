from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
from ..models.schemas import TimetableRawResp
from .deps import get_current_user
from ..storage.session_store import get_sso
from ..services.timetable import fetch_kblist, TimetableFetchError

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