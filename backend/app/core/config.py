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
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "https://lively-sand-05dbb8b0f.1.azurestaticapps.net",
        "capacitor://localhost",
        "ionic://localhost",
    ]

    SQL_SERVER: str | None = None
    SQL_DB: str | None = None
    SQL_USER: str | None = None
    SQL_PASSWORD: str | None = None
    # Timeout de conexión en segundos. Aumentar si hay latencia o firewall lento.
    SQL_CONNECTION_TIMEOUT: int = 60
    # TrustServerCertificate=yes para SQL Server local o dev sin certificado válido.
    SQL_TRUST_SERVER_CERTIFICATE: bool = False
    SQL_USUARIO_TABLE: str = "MaestroUsuarios"
    # Cache de usuario por nombre para login (segundos). 0 = desactivado.
    SQL_LOGIN_CACHE_TTL_SEC: int = 60
    # Cache de catálogos (categorías, subcategorías, reglas, presupuestos) por id_usuario. 0 = desactivado.
    SQL_CATALOG_CACHE_TTL_SEC: int = 300

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
