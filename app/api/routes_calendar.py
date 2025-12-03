from fastapi import APIRouter, Query
from ..models.schemas import CalendarResp

router = APIRouter()

@router.get("", response_model=CalendarResp)
async def get_calendar(date_from: str = Query(...), date_to: str = Query(...)):
    # TODO: 展开 sessions + 合并自定义事件
    return {"code": 0, "message": "ok", "data": []}