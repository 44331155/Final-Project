from fastapi import APIRouter
from .routes_auth import router as auth_router
from .routes_timetable import router as timetable_router
from .routes_calendar import router as calendar_router
from .routes_events import router as events_router
from .routes_system import router as system_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(timetable_router, prefix="/timetable", tags=["timetable"])
api_router.include_router(calendar_router, prefix="/calendar", tags=["calendar"])
api_router.include_router(events_router, prefix="/events", tags=["events"])
api_router.include_router(system_router, prefix="/system", tags=["system"])