import time
import jwt
import sqlite3
from fastapi import APIRouter, HTTPException

from ..models.schemas import LoginReq, LoginResp
from ..services.sso import get_sso_cookie
from ..config import settings
from ..storage.session_store import set_sso
from ..storage.db import get_conn, init_schema
from ..security import encrypt_password # 导入加密函数

router = APIRouter()

def _upsert_user_credentials(conn: sqlite3.Connection, username: str, password: str):
    """插入或更新用户的加密密码"""
    encrypted_pwd = encrypt_password(password)
    # 尝试更新，如果用户不存在则插入
    cur = conn.execute("UPDATE users SET password_encrypted = ? WHERE username = ?", (encrypted_pwd, username))
    if cur.rowcount == 0:
        conn.execute("INSERT INTO users (username, password_encrypted) VALUES (?, ?)", (username, encrypted_pwd))
    conn.commit()


@router.post("/login", response_model=LoginResp)
async def login(req: LoginReq):
    try:
        sso_cookie = await get_sso_cookie(req.username, req.password)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"登录失败: {e}")

    # --- 新增逻辑：保存或更新用户凭证 ---
    conn = get_conn(settings.DB_PATH)
    try:
        init_schema(conn) # 确保表存在
        _upsert_user_credentials(conn, req.username, req.password)
    except Exception as db_err:
        # 即使数据库操作失败，本次登录也应该成功，只是无法自动续期
        # 此处可以添加日志记录
        print(f"警告: 存储用户凭证失败: {db_err}")
    finally:
        conn.close()
    # --- 新增逻辑结束 ---

    # 将 SSO 凭证保存到服务端“短期会话存储”
    set_sso(req.username, sso_cookie, ttl_seconds=3300)

    token = jwt.encode(
        {"sub": req.username, "exp": int(time.time()) + 3600},
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    return {"code": 0, "message": "ok", "data": {"token": token}}