from fastapi import FastAPI
from fastapi.security import HTTPBearer
from .api.router import api_router

app = FastAPI(
    title="Schedule Backend",
    version="0.1.0",
    # 添加安全定义（可选）
    openapi_tags=[
        {"name": "auth", "description": "认证与登录"},
        {"name": "timetable", "description": "课表相关"},
        {"name": "calendar", "description": "日历合并"},
        {"name": "events", "description": "自定义事件"}
    ]
)

security = HTTPBearer()

app.include_router(api_router, prefix="/api")

@app.get("/healthz")
def healthz():
    return {"ok": True}