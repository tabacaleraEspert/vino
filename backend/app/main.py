from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="Finanzas Personales API",
    version=settings.APP_VERSION,
)

# CORS: Azure Portal puede tener su propia CORS que anula esta. Si falla, en Portal → CORS
# vacía todos los orígenes para que la app maneje CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://lively-sand-05dbb8b0f.1.azurestaticapps.net",
        *settings.CORS_ORIGINS,
    ],
    allow_origin_regex=r"https://[a-zA-Z0-9.-]+\.azurestaticapps\.net",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")
