from fastapi import APIRouter
from app.api.v1.views.dashboard import router as dashboard_router
from app.api.v1.views.home import router as home_router
from app.api.v1.views.admin_dashboard import router as admin_dash_router
from app.api.v1.views.budget import router as budget_router

router = APIRouter()
router.include_router(dashboard_router, tags=["views"])
# Home routes: /views/home/summary, /views/home/breakdown
router.include_router(home_router, prefix="/home", tags=["views"])
# Admin monitor panel
router.include_router(admin_dash_router, prefix="/admin", tags=["views"])
# Budget analysis: /views/budget/status, /views/budget/suggestions
router.include_router(budget_router, prefix="/budget", tags=["views"])
