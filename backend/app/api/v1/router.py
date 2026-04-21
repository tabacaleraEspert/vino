from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.bootstrap import router as bootstrap_router
from app.api.v1 import movimientos
from app.api.v1 import categorias
from app.api.v1 import subcategorias
from app.api.v1 import reglas
from app.api.v1 import presupuestos
from app.api.v1 import recategorizaciones
from app.api.v1 import comercios
from app.api.v1.admin import router as admin_router
from app.api.v1.views import router as views_router

router = APIRouter()

# Public routes
router.include_router(health_router, tags=["health"])
router.include_router(auth_router, prefix="/auth", tags=["auth"])

# Admin (protected by master key internally)
router.include_router(admin_router, prefix="/admin", tags=["admin"])

# Authenticated routes (auth handled via Depends in each endpoint)
router.include_router(bootstrap_router, prefix="/bootstrap", tags=["bootstrap"])
router.include_router(comercios.router, prefix="/comercios", tags=["comercios"])
router.include_router(views_router, prefix="/views", tags=["views"])
router.include_router(movimientos.router, prefix="/movimientos", tags=["movimientos"])
router.include_router(categorias.router, prefix="/categorias", tags=["catalogo"])
router.include_router(subcategorias.router, prefix="/subcategorias", tags=["catalogo"])
router.include_router(reglas.router, prefix="/reglas", tags=["catalogo"])
router.include_router(presupuestos.router, prefix="/presupuestos", tags=["catalogo"])
router.include_router(recategorizaciones.router, prefix="/recategorizaciones", tags=["recategorizacion"])
