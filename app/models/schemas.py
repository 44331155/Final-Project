from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class CommonResp(BaseModel):
    code: int
    message: str

class LoginReq(BaseModel):
    username: str
    password: str

class LoginData(BaseModel):
    token: str

class LoginResp(CommonResp):
    data: LoginData

# 原始课表返回：仅包含 kbList 数组
class TimetableRawData(BaseModel):
    kbList: List[Dict[str, Any]]

class TimetableRawResp(CommonResp):
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

class EventCreateReq(BaseModel):
    title: str
    startTime: str
    endTime: str
    place: Optional[str] = None