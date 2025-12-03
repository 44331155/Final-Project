from fastapi import APIRouter, HTTPException
from ..models.schemas import LoginReq, LoginResp
from ..services.sso import get_sso_cookie
import time, jwt
from ..config import settings
from ..storage.session_store import set_sso

router = APIRouter()

@router.post("/login", response_model=LoginResp)
async def login(req: LoginReq):
    try:
        sso_cookie = await get_sso_cookie(req.username, req.password)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"登录失败: {e}")

    # 将 SSO 凭证保存到服务端“短期会话存储”
    set_sso(req.username, sso_cookie, ttl_seconds=3300)

    token = jwt.encode(
        {"sub": req.username, "exp": int(time.time()) + 3600},
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    return {"code": 0, "message": "ok", "data": {"token": token}}