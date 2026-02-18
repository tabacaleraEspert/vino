from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_VERSION: str = "0.1.0"
    ENV: str = "local"

    JWT_SECRET: str = "dev_change_me"
    JWT_EXPIRE_MIN: int = 60 * 24
    MASTER_KEY: str = "dev_master_change_me"
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "https://lively-sand-05dbb8b0f.1.azurestaticapps.net",
    ]

    SQL_SERVER: str | None = None
    SQL_DB: str | None = None
    SQL_USER: str | None = None
    SQL_PASSWORD: str | None = None
    SQL_USUARIO_TABLE: str = "MaestroUsuarios"
    # Cache de usuario por nombre para login (segundos). 0 = desactivado.
    SQL_LOGIN_CACHE_TTL_SEC: int = 60
    GOOGLE_SHEETS_CREDENTIALS_FILE: str | None = None
    GOOGLE_SHEETS_CREDENTIALS_JSON: str | None = None
    SHEETS_REGISTRY_JSON: str | None = None
    # Fallback solo para scripts/dev; en producción viene de ID_Sheets (MaestroUsuarios)
    SPREADSHEET_ID: str | None = None
    # Cache in-memory para read_table (segundos). 0 = desactivado.
    SHEETS_CACHE_TTL_SEC: int = 120
    # Refresco periódico de cache (segundos). 0 = desactivado. Solo si SPREADSHEET_ID está set.
    SHEETS_REFRESH_INTERVAL_SEC: int = 300

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
