from pydantic import BaseModel, Field
from typing import Optional, Any, List, Dict, Union

class CommonResp(BaseModel):
    code: int = 0
    message: str = "ok"
    # 关键修改：明确指定 data 的类型，并提供一个工厂默认值
    # 这能更好地帮助 FastAPI/Pydantic 处理空列表的情况
    data: Union[List, Dict, None] = None

class LoginReq(BaseModel):
    username: str
    password: str

class WeChatBindReq(BaseModel):
    code: str

class WeChatLoginReq(BaseModel):
    code: str

class LoginData(BaseModel):
    token: str
    is_wechat_bound: bool = False  # 新增字段

class LoginResp(CommonResp):
    data: Optional[LoginData] = None

# 原始课表返回：仅包含 kbList 数组
class TimetableRawData(BaseModel):
    kbList: List[Dict[str, Any]]

class TimetableRawResp(BaseModel):
    data: TimetableRawData

# 其余原有模型（如 Calendar、Events）保留
class CalendarEvent(BaseModel):
    title: str
    startTime: str
    endTime: str
    type: str = "course"
    place: Optional[str] = None

class CalendarResp(CommonResp):
    data: List[CalendarEvent]

class EventReq(BaseModel):
    title: str
    startTime: str
    endTime: str
    place: Optional[str] = None

# 添加以下模型
class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str