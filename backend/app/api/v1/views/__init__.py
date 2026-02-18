from fastapi import APIRouter
from app.api.v1.views.dashboard import router as dashboard_router
from app.api.v1.views.home import router as home_router

router = APIRouter()
router.include_router(dashboard_router, tags=["views"])
router.include_router(home_router, prefix="/home", tags=["views"])
