from fastapi import APIRouter, Query, Depends, HTTPException
from ..models.schemas import TimetableResp
from .deps import get_current_user
from ..storage.session_store import get_sso
from ..services.timetable import fetch_and_parse_timetable, TimetableFetchError

router = APIRouter()

@router.get("", response_model=TimetableResp)
async def get_timetable(
    semester: str = Query(..., description="例如 2024-2025-1 / 2024-2025-2"),
    username: str = Depends(get_current_user),
):
    sso_cookie = get_sso(username)
    if not sso_cookie:
        raise HTTPException(status_code=401, detail="登录态已过期，请重新登录")

    try:
        data = await fetch_and_parse_timetable(sso_cookie, semester)
    except TimetableFetchError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"未知错误: {e}")

    return {"code": 0, "message": "ok", "data": data}