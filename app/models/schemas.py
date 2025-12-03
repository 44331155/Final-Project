from pydantic import BaseModel
from typing import List, Optional

# 通用响应
class CommonResp(BaseModel):
    code: int
    message: str

# 登录
class LoginReq(BaseModel):
    username: str
    password: str

class LoginData(BaseModel):
    token: str

class LoginResp(CommonResp):
    data: LoginData

# 课表
class Course(BaseModel):
    id: Optional[int] = None
    code: Optional[str] = None
    name: str
    teacher: Optional[str] = None

class Session(BaseModel):
    courseCode: Optional[str] = None
    courseName: str
    weekday: int            # 1-7
    start_slot: int
    end_slot: int
    classroom: Optional[str] = None
    weeks: Optional[List[int]] = None

class TimetableData(BaseModel):
    courses: List[Course]
    sessions: List[Session]

class TimetableResp(CommonResp):
    data: TimetableData

# 日历
class CalendarEvent(BaseModel):
    title: str
    startTime: str
    endTime: str
    type: str = "course"
    place: Optional[str] = None

class CalendarResp(CommonResp):
    data: List[CalendarEvent]

# 自定义事件
class EventCreateReq(BaseModel):
    title: str
    startTime: str
    endTime: str
    place: Optional[str] = None