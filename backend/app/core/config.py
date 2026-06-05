from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_VERSION: str = "0.1.0"
    ENV: str = "local"

    JWT_SECRET: str = "dev_change_me"
    JWT_EXPIRE_MIN: int = 60 * 24
    MASTER_KEY: str = "dev_master_change_me"
    OPENAI_API_KEY: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_IOS_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GMAIL_TOKEN_KEY: str = ""  # Fernet key for encrypting Gmail refresh tokens
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM: str = ""  # whatsapp:+1234567890
    TWILIO_OTP_CONTENT_SID: str = ""  # Content Template SID for OTP (e.g. HXXXXXXXXXXX)
    TWILIO_REMINDER_CONTENT_SID: str = ""  # Content Template SID for inactivity reminder
    ADMIN_USER_IDS: list[int] = [8, 11]  # Davor, Nacho — can access admin pipeline log
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        # Firebase Hosting (producción)
        "https://ahorros-app-46e0e.web.app",
        "https://ahorros-app-46e0e.firebaseapp.com",
        # Azure legacy (mantener mientras haya usuarios en la versión vieja)
        "https://lively-sand-05dbb8b0f.1.azurestaticapps.net",
        "capacitor://localhost",
        "ionic://localhost",
    ]

    # PostgreSQL/Neon connection URL (asyncpg)
    DATABASE_URL: str = ""

    # Legacy SQL Server fields (kept for reference, no longer used)
    SQL_SERVER: str | None = None
    SQL_DB: str | None = None
    SQL_USER: str | None = None
    SQL_PASSWORD: str | None = None
    SQL_CONNECTION_TIMEOUT: int = 60
    SQL_TRUST_SERVER_CERTIFICATE: bool = False
    SQL_USUARIO_TABLE: str = "MaestroUsuarios"
    SQL_LOGIN_CACHE_TTL_SEC: int = 60
    SQL_CATALOG_CACHE_TTL_SEC: int = 300

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
