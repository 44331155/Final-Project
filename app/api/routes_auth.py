import time
import jwt
import sqlite3
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..models.schemas import LoginReq, LoginResp, WeChatBindReq, WeChatLoginReq, CommonResp
from ..services.sso import get_sso_cookie
from ..services.wechat import get_openid_from_code # 导入微信服务
from ..config import settings
from ..storage.session_store import set_sso
from ..storage.db import get_conn, init_schema
from ..security import encrypt_password # 导入加密函数
from .deps import get_current_user # 导入 get_current_user

router = APIRouter()

# 辅助函数：检查用户是否绑定微信
def _check_is_bound(conn: sqlite3.Connection, username: str) -> bool:
    cur = conn.execute("SELECT wechat_openid FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    # 如果 row 存在且 wechat_openid 不为空，则视为已绑定
    return bool(row and row[0])

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
    is_bound = False
    try:
        init_schema(conn) # 确保表存在
        _upsert_user_credentials(conn, req.username, req.password)
        is_bound = _check_is_bound(conn, req.username)
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
    # 修改返回逻辑
    return {
        "code": 0, 
        "message": "ok", 
        "data": {
            "token": token, 
            "is_wechat_bound": is_bound
        }
    }

@router.post("/bind-wechat", response_model=CommonResp)
async def bind_wechat(
    req: WeChatBindReq,
    username: str = Depends(get_current_user)
):
    """
    将当前登录的用户账号与微信 openid 绑定。
    """
    openid = await get_openid_from_code(req.code)
    conn = get_conn(settings.DB_PATH)
    try:
        # 将 openid 更新到当前用户的记录中
        cur = conn.execute(
            "UPDATE users SET wechat_openid = ? WHERE username = ?",
            (openid, username)
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="用户不存在")
    except sqlite3.IntegrityError:
        # UNIQUE 约束失败，意味着 openid 已被其他账号绑定
        raise HTTPException(status_code=400, detail="绑定失败，该微信已绑定其他账号")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库操作失败: {e}")
    finally:
        conn.close()
    
    return CommonResp(code=0, message="绑定成功")


@router.post("/login-by-wechat", response_model=LoginResp)
async def login_by_wechat(req: WeChatLoginReq):
    """
    使用微信 code 进行免密登录。
    """
    openid = await get_openid_from_code(req.code)
    conn = get_conn(settings.DB_PATH)
    conn.row_factory = sqlite3.Row # 确保可以按列名访问
    try:
        cur = conn.execute("SELECT username FROM users WHERE wechat_openid = ?", (openid,))
        user = cur.fetchone()
    finally:
        conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="该微信未绑定账号")

    username = user["username"]
    # 生成新的 JWT Token
    token = jwt.encode(
        {"sub": username, "exp": int(time.time()) + 3600},
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    # 既然是用微信登录的，那肯定是绑定过的，直接返回 True
    return LoginResp(
        code=0, 
        message="ok", 
        data={
            "token": token, 
            "is_wechat_bound": True
        }
    )

class UserInfoResp(CommonResp):
    data: dict

@router.get("/me", response_model=UserInfoResp)
async def get_my_info(username: str = Depends(get_current_user)):
    """
    获取当前登录用户的基本信息（包括绑定状态）
    """
    conn = get_conn(settings.DB_PATH)
    try:
        is_bound = _check_is_bound(conn, username)
    finally:
        conn.close()
        
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "username": username,
            "is_wechat_bound": is_bound
        }
    }

@router.post("/unbind-wechat", response_model=CommonResp)
async def unbind_wechat(username: str = Depends(get_current_user)):
    """
    解除当前登录用户与微信的绑定。
    """
    conn = get_conn(settings.DB_PATH)
    try:
        cur = conn.execute(
            "SELECT wechat_openid FROM users WHERE username = ?",
            (username,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        if not row[0]:
            raise HTTPException(status_code=400, detail={"code": 123, "detail": "未绑定微信"})
        conn.execute(
            "UPDATE users SET wechat_openid = NULL WHERE username = ?",
            (username,)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"数据库操作失败: {e}")
    finally:
        conn.close()

    return CommonResp(code=0, message="ok", data={"is_wechat_bound": False})