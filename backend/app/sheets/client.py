import json
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.core.config import settings

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_sheets_service():
    """
    Credenciales: 1) GOOGLE_SHEETS_CREDENTIALS_JSON (env, ej. Azure App Settings)
    2) Fallback: GOOGLE_SHEETS_CREDENTIALS_FILE (ruta al .json)
    """
    creds_json = settings.GOOGLE_SHEETS_CREDENTIALS_JSON
    if creds_json:
        info = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        path = settings.GOOGLE_SHEETS_CREDENTIALS_FILE or "creds/service-account.json"
        if not Path(path).exists():
            raise RuntimeError(
                "Falta GOOGLE_SHEETS_CREDENTIALS_JSON o GOOGLE_SHEETS_CREDENTIALS_FILE con archivo existente"
            )
        creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)

    return build("sheets", "v4", credentials=creds, cache_discovery=False)
