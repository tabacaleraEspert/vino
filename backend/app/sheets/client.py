import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.core.config import settings

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheets_service():
    info = None

    if settings.GOOGLE_SHEETS_CREDENTIALS_FILE:
        with open(settings.GOOGLE_SHEETS_CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            info = json.load(f)
    elif settings.GOOGLE_SHEETS_CREDENTIALS_JSON:
        info = json.loads(settings.GOOGLE_SHEETS_CREDENTIALS_JSON)
    else:
        raise RuntimeError("Falta GOOGLE_SHEETS_CREDENTIALS_FILE o GOOGLE_SHEETS_CREDENTIALS_JSON en .env")

    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)
