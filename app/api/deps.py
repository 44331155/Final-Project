from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
import sqlite3

from ..config import settings
from ..storage.session_store import get_sso, set_sso
from ..storage.db import get_conn
from ..services.sso import get_sso_cookie
from ..security import decrypt_password

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """解码JWT，获取用户名"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="无效的认证凭证")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="无效的认证凭证")

async def get_valid_sso_cookie(username: str = Depends(get_current_user)) -> str:
    """
    获取有效的SSO Cookie。如果过期，则尝试自动重新登录。
    """
    # 1. 尝试从会话存储中获取 cookie
    sso_cookie = get_sso(username)
    if sso_cookie:
        return sso_cookie

    # 2. 如果 cookie 不存在或已过期，尝试自动续期
    print(f"SSO会话已过期，正在为用户 '{username}' 尝试自动续期...")
    conn = get_conn(settings.DB_PATH)
    try:
        # 从数据库获取加密的密码
        cur = conn.execute("SELECT password_encrypted FROM users WHERE username = ?", (username,))
        user_row = cur.fetchone()
        if not user_row:
            raise HTTPException(status_code=401, detail="无法自动续期：找不到用户凭证")

        # 解密密码并重新登录
        decrypted_password = decrypt_password(user_row["password_encrypted"])
        new_sso_cookie = await get_sso_cookie(username, decrypted_password)
        
        # 存储新的 cookie
        set_sso(username, new_sso_cookie, ttl_seconds=3300)
        print(f"用户 '{username}' 自动续期成功。")
        return new_sso_cookie

    except Exception as e:
        # 自动续期失败，要求用户重新登录
        print(f"用户 '{username}' 自动续期失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录态已过期，请重新登录",
        )
    finally:
        conn.close()