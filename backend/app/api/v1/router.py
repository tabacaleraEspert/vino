from fastapi import APIRouter, Depends

from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.movimientos import router as movimientos_router
from app.api.v1.reglas import router as reglas_router
from app.api.v1.categorias import router as categorias_router
from app.api.v1.comercios import router as comercios_router
from app.api.v1.views import router as views_router
from app.api.v1.admin import router as admin_router
from app.api.v1 import movimientos
from app.api.v1 import categorias
from app.api.v1 import subcategorias
from app.api.v1 import reglas
from app.api.v1 import presupuestos
from app.api.v1 import comercios
from app.api.v1 import views
from app.api.v1 import admin
from app.core.security import require_user

# Rutas que requieren autenticación (usan Sheets del usuario)
auth_dep = Depends(require_user)

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(admin_router, prefix="/admin", tags=["admin"])
router.include_router(comercios_router, prefix="/comercios", tags=["comercios"], dependencies=[auth_dep])
router.include_router(views_router, prefix="/views", tags=["views"], dependencies=[auth_dep])
router.include_router(movimientos.router, prefix="/movimientos", tags=["movimientos"], dependencies=[auth_dep])
router.include_router(categorias.router, prefix="/categorias", tags=["catalogo"], dependencies=[auth_dep])
router.include_router(subcategorias.router, prefix="/subcategorias", tags=["catalogo"], dependencies=[auth_dep])
router.include_router(reglas.router, prefix="/reglas", tags=["catalogo"], dependencies=[auth_dep])
router.include_router(presupuestos.router, prefix="/presupuestos", tags=["catalogo"], dependencies=[auth_dep])