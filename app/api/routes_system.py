from fastapi import APIRouter
from ..config import settings
from typing import List, Dict

router = APIRouter()

@router.get("/terms")
async def get_term_configs():
    """
    获取所有学期的配置信息（学期ID和该学期第一周的周一日期）
    """
    term_list = [
        {"id": term_id, "start_monday": config["start_monday"].isoformat()}
        for term_id, config in settings.TERM_CONFIGS.items()
    ]
    # 按学期ID降序排序，让最新的学期显示在最前面
    term_list.sort(key=lambda x: x["id"], reverse=True)
    return {"code": 0, "message": "ok", "data": term_list}