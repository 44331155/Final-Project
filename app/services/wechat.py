import httpx
from fastapi import HTTPException
from ..config import settings

async def get_openid_from_code(code: str) -> str:
    """
    使用临时 code 从微信服务器换取 openid。
    """
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.WECHAT_APPID,
        "secret": settings.WECHAT_APPSECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            raise HTTPException(status_code=500, detail=f"请求微信服务器失败: {e}")

    if "errcode" in data and data["errcode"] != 0:
        raise HTTPException(status_code=400, detail=f"微信登录凭证无效: {data.get('errmsg')}")
    
    openid = data.get("openid")
    if not openid:
        raise HTTPException(status_code=500, detail="未能从微信获取 openid")
        
    return openid