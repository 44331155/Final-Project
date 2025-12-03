from fastapi import APIRouter
from ..models.schemas import EventCreateReq, CommonResp

router = APIRouter()

@router.post("", response_model=CommonResp)
async def add_event(req: EventCreateReq):
    # TODO: 写入 SQLite
    return {"code": 0, "message": "ok"}