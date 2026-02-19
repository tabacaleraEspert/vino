"""
Script auxiliar: sincroniza Categoria y SubCategoria desde Google Sheets a Azure SQL.
Usa MERGE para upsert. Ejecutar: python -m scripts.sync_sheets_to_sql

Env vars (o .env):
  - GOOGLE_SHEETS_CREDENTIALS_JSON o GOOGLE_SHEETS_CREDENTIALS_FILE
  - SPREADSHEET_ID (o GOOGLE_SHEETS_SPREADSHEET_ID)
  - AZURE_SQL_CONN_STR, o bien SQL_SERVER, SQL_DB, SQL_USER, SQL_PASSWORD
"""
import json
import os
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pyodbc

# Cargar .env desde backend
_backend_root = Path(__file__).resolve().parent.parent
_env = _backend_root / ".env"
if _env.exists():
    for line in _env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# Credenciales Google (antes de importar app)
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


# =========================
# Config
# =========================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

SHEET_TAB_CATEGORIA = "Categoria"
SHEET_TAB_SUBCATEGORIA = "SubCategoria"  # OJO: el nombre debe matchear exacto tu tab


def utcnow():
    return datetime.now(timezone.utc)


def parse_int(v) -> Optional[int]:
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        return int(float(s))  # tolera "1.0"
    except Exception:
        return None


def parse_str(v, default="") -> str:
    if v is None:
        return default
    s = str(v).strip()
    return s if s != "" else default


def parse_timestamp(v) -> Optional[datetime]:
    """
    Intenta parsear Timestamp de Sheets.
    Acepta ISO, 'YYYY-MM-DD HH:MM:SS', etc.
    Si no parsea, devuelve None y SQL usará SYSUTCDATETIME().
    """
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None

    # Normalizaciones simples
    s = s.replace("T", " ").replace("Z", "")

    # Intentos comunes
    fmts = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%Y-%m-%d",
    ]
    for f in fmts:
        try:
            dt = datetime.strptime(s, f)
            # Si viene naive, asumir UTC
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def sha256_row(d: Dict[str, Any]) -> bytes:
    """
    Hash estable del row normalizado (útil para futuro).
    """
    payload = json.dumps(d, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(payload).digest()


def get_sheets_service():
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
    creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")

    if creds_json:
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    elif creds_file:
        path = Path(creds_file)
        if not path.is_absolute():
            path = _backend_root / creds_file
        creds = Credentials.from_service_account_file(str(path), scopes=SCOPES)
    else:
        raise RuntimeError("Falta GOOGLE_SHEETS_CREDENTIALS_JSON o GOOGLE_SHEETS_CREDENTIALS_FILE")

    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def read_sheet_table(service, spreadsheet_id: str, tab_name: str) -> List[Dict[str, Any]]:
    """
    Lee toda la pestaña como tabla: primera fila headers.
    Devuelve lista de dicts (row).
    """
    rng = f"{tab_name}!A:Z"
    resp = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=rng).execute()
    values = resp.get("values", [])

    if not values or len(values) < 2:
        return []

    headers = [h.strip() for h in values[0]]
    out = []
    for r in values[1:]:
        row = {}
        for i, h in enumerate(headers):
            row[h] = r[i] if i < len(r) else None
        # Ignorar filas completamente vacías
        if all((row.get(h) is None or str(row.get(h)).strip() == "") for h in headers):
            continue
        out.append(row)
    return out


def get_sql_conn():
    conn_str = os.getenv("AZURE_SQL_CONN_STR")
    if not conn_str:
        server = os.getenv("SQL_SERVER")
        db = os.getenv("SQL_DB")
        user = os.getenv("SQL_USER")
        pwd = os.getenv("SQL_PASSWORD")
        if not all([server, db, user, pwd]):
            raise RuntimeError(
                "Falta AZURE_SQL_CONN_STR o bien SQL_SERVER, SQL_DB, SQL_USER, SQL_PASSWORD"
            )
        driver = "{ODBC Driver 18 for SQL Server}"
        conn_str = (
            f"Driver={driver};Server={server},1433;Database={db};"
            f"Uid={user};Pwd={pwd};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        )
    return pyodbc.connect(conn_str, autocommit=False)


SQL_MERGE_CATEGORIA = """
MERGE dbo.Categoria AS T
USING (SELECT
  ? AS Id_usuario,
  ? AS Source_Id,
  ? AS Nombre,
  ? AS Icon,
  ? AS Color,
  ? AS [Timestamp]
) AS S
ON (T.Id_usuario = S.Id_usuario AND T.Source_Id = S.Source_Id)
WHEN MATCHED THEN
  UPDATE SET
    T.Nombre = S.Nombre,
    T.Icon = S.Icon,
    T.Color = S.Color,
    T.[Timestamp] = COALESCE(S.[Timestamp], SYSUTCDATETIME())
WHEN NOT MATCHED THEN
  INSERT (Id_usuario, Source_Id, Nombre, Icon, Color, [Timestamp])
  VALUES (S.Id_usuario, S.Source_Id, S.Nombre, S.Icon, S.Color, COALESCE(S.[Timestamp], SYSUTCDATETIME()));
"""

SQL_GET_CATEGORIA_IDSQL = """
SELECT TOP 1 Id
FROM dbo.Categoria
WHERE Id_usuario = ? AND Source_Id = ?;
"""

SQL_MERGE_SUBCATEGORIA = """
MERGE dbo.SubCategoria AS T
USING (SELECT
  ? AS Id_Categoria,
  ? AS Source_Id,
  ? AS Nombre_SubCategoria,
  ? AS [Timestamp]
) AS S
ON (T.Id_Categoria = S.Id_Categoria AND T.Source_Id = S.Source_Id)
WHEN MATCHED THEN
  UPDATE SET
    T.Nombre_SubCategoria = S.Nombre_SubCategoria,
    T.[Timestamp] = COALESCE(S.[Timestamp], SYSUTCDATETIME())
WHEN NOT MATCHED THEN
  INSERT (Id_Categoria, Source_Id, Nombre_SubCategoria, [Timestamp])
  VALUES (S.Id_Categoria, S.Source_Id, S.Nombre_SubCategoria, COALESCE(S.[Timestamp], SYSUTCDATETIME()));
"""


def sync_categoria(cur, rows: List[Dict[str, Any]]) -> Tuple[int, int]:
    ok = 0
    skipped = 0
    for row in rows:
        # Headers reales: Id, Nombre, Icon, Color, Timestamp, Id_usuario
        id_usuario = parse_int(row.get("Id_usuario"))
        source_id = parse_int(row.get("Id"))
        nombre = parse_str(row.get("Nombre"))
        icon = parse_str(row.get("Icon"), default="📁")
        color = parse_str(row.get("Color"), default="#6b7280")
        ts = parse_timestamp(row.get("Timestamp"))

        if id_usuario is None or source_id is None or nombre == "":
            skipped += 1
            continue

        cur.execute(SQL_MERGE_CATEGORIA, (id_usuario, source_id, nombre, icon, color, ts))
        ok += 1
    return ok, skipped


def sync_subcategoria(cur, rows: List[Dict[str, Any]]) -> Tuple[int, int, int]:
    ok = 0
    skipped = 0
    missing_fk = 0

    for row in rows:
        # Headers reales: Id_Categoria, Nombre_Categoria, Id, Nombre_SubCategoria, Timestamp, Id_usuario
        id_usuario = parse_int(row.get("Id_usuario"))
        source_cat_id = parse_int(row.get("Id_Categoria"))
        source_sub_id = parse_int(row.get("Id"))
        nombre_sub = parse_str(row.get("Nombre_SubCategoria"))
        ts = parse_timestamp(row.get("Timestamp"))

        if id_usuario is None or source_cat_id is None or source_sub_id is None or nombre_sub == "":
            skipped += 1
            continue

        cur.execute(SQL_GET_CATEGORIA_IDSQL, (id_usuario, source_cat_id))
        r = cur.fetchone()
        if not r:
            missing_fk += 1
            continue
        id_categoria_sql = int(r[0])

        cur.execute(SQL_MERGE_SUBCATEGORIA, (id_categoria_sql, source_sub_id, nombre_sub, ts))
        ok += 1

    return ok, skipped, missing_fk


def main():
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID") or os.getenv("SPREADSHEET_ID")
    if not spreadsheet_id:
        raise RuntimeError("Falta GOOGLE_SHEETS_SPREADSHEET_ID o SPREADSHEET_ID")

    svc = get_sheets_service()

    # 1) Leer Sheets
    cat_rows = read_sheet_table(svc, spreadsheet_id, SHEET_TAB_CATEGORIA)
    sub_rows = read_sheet_table(svc, spreadsheet_id, SHEET_TAB_SUBCATEGORIA)

    print(f"[Sheets] Categoria rows: {len(cat_rows)}")
    print(f"[Sheets] SubCategoria rows: {len(sub_rows)}")

    # 2) Sync a SQL
    conn = get_sql_conn()
    try:
        cur = conn.cursor()

        ok_cat, skip_cat = sync_categoria(cur, cat_rows)
        conn.commit()
        print(f"[SQL] Categoria upsert ok={ok_cat} skipped={skip_cat}")

        ok_sub, skip_sub, missing_fk = sync_subcategoria(cur, sub_rows)
        conn.commit()
        print(f"[SQL] SubCategoria upsert ok={ok_sub} skipped={skip_sub} missing_fk={missing_fk}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
