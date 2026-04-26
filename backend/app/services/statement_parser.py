"""Service for extracting transactions from bank statements using OpenAI."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


_SYSTEM_PROMPT = """Sos un extractor de transacciones financieras de resumenes bancarios y de tarjetas de credito argentinas.

Extrae TODAS las transacciones/movimientos del documento. Para cada una devolvé:
- fecha: en formato YYYY-MM-DD. Si solo hay mes/año, usá el día 1.
- descripcion: nombre del comercio o descripción tal como aparece, limpio y legible.
- monto: número positivo (sin signo, sin $ ni separadores de miles). Decimales con punto.
- moneda: "ARS", "USD", etc. Si no se indica, asumir ARS.
- tipo: "Gasto" para compras/débitos, "Ingreso" para créditos/pagos a favor.

Las categorías disponibles del usuario son:
{categories_json}

Para cada transacción, sugerí:
- categoria_id: el ID de la categoría que mejor aplica (o null si no estás seguro)
- subcategoria_id: el ID de la subcategoría que mejor aplica (o null)

NO incluyas:
- Totales, subtotales, saldos anteriores, impuestos globales, intereses del resumen
- Filas que sean encabezados o resúmenes

Respondé SOLO con JSON válido:
{
  "transactions": [
    {
      "fecha": "2026-04-15",
      "descripcion": "MERCADOLIBRE",
      "monto": 15000.50,
      "moneda": "ARS",
      "tipo": "Gasto",
      "categoria_id": 3,
      "subcategoria_id": 12
    }
  ],
  "statement_period": "2026-04",
  "card_or_account": "Visa terminada en 1234"
}"""


def _build_categories_json(categories: list[dict[str, Any]]) -> str:
    """Build a compact JSON of categories for the AI prompt."""
    cats = []
    for c in categories:
        entry: dict[str, Any] = {"id": c.get("id"), "nombre": c.get("nombre", "")}
        subs = c.get("subcategorias", [])
        if subs:
            entry["subcategorias"] = [
                {"id": s.get("id"), "nombre": s.get("nombre", "")} for s in subs
            ]
        cats.append(entry)
    return json.dumps(cats, ensure_ascii=False)


def make_origen_id(fecha: str, monto: float, descripcion: str) -> str:
    """Generate a deterministic origin ID for deduplication."""
    raw = f"{fecha}_{monto}_{descripcion}".lower().strip()
    return f"stmt_{hashlib.md5(raw.encode()).hexdigest()[:12]}"


async def extract_from_text(text: str, categories: list[dict]) -> dict:
    """Extract transactions from plain text (PDF text extraction)."""
    client = _get_client()
    prompt = _SYSTEM_PROMPT.replace("{categories_json}", _build_categories_json(categories))

    response = await client.chat.completions.create(
        model="gpt-5.5",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Extracto bancario:\n\n{text}"},
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=4000,
    )

    raw = response.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse OpenAI response as JSON: %s", raw[:200])
        return {"transactions": [], "error": "No se pudo parsear la respuesta"}


async def extract_from_image(image_bytes: bytes, mime_type: str, categories: list[dict]) -> dict:
    """Extract transactions from an image using Vision API."""
    client = _get_client()
    prompt = _SYSTEM_PROMPT.replace("{categories_json}", _build_categories_json(categories))
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    response = await client.chat.completions.create(
        model="gpt-5.5",
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extraé las transacciones de este extracto bancario:"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64}", "detail": "high"},
                    },
                ],
            },
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=4000,
    )

    raw = response.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse Vision response as JSON: %s", raw[:200])
        return {"transactions": [], "error": "No se pudo parsear la respuesta"}


async def extract_from_pdf(pdf_bytes: bytes, categories: list[dict]) -> dict:
    """Extract transactions from a PDF. Tries text extraction first, falls back to images."""
    from PyPDF2 import PdfReader
    import io

    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)

    full_text = "\n\n--- Página ---\n\n".join(pages_text)

    # If text extraction worked (>100 chars), use text mode
    if len(full_text.strip()) > 100:
        return await extract_from_text(full_text, categories)

    # Sparse text = scanned PDF, send first page as image
    # For now, return an error suggesting to use an image instead
    return {
        "transactions": [],
        "error": "El PDF parece ser escaneado. Probá subiendo una foto o screenshot del extracto.",
    }


def _parse_ar_money(val: str | None) -> float | None:
    """Parse Argentine money format: $1.219.066,31 → 1219066.31, U$S698,57 → 698.57"""
    if not val:
        return None
    s = str(val).strip()
    if not s or s == "None":
        return None
    # Remove currency symbols and spaces (order matters: U$S before $)
    for sym in ("U$S", "US$", "u$s", "us$", "$"):
        s = s.replace(sym, "")
    s = s.strip()
    if not s:
        return None
    # Handle negative: $-5.795.296,50
    negative = False
    if s.startswith("-"):
        negative = True
        s = s[1:]
    # Argentine format: dots are thousands, comma is decimal
    s = s.replace(".", "").replace(",", ".")
    try:
        val_f = float(s)
        return -val_f if negative else val_f
    except ValueError:
        return None


def _is_header_row(row_values: list) -> bool:
    """Check if a row is a header row (Fecha | Descripción | ...)."""
    vals = [str(v or "").strip().lower() for v in row_values]
    return "fecha" in vals and "descripción" in vals


def _is_section_header(row_values: list) -> str | None:
    """Detect section headers like 'Pago de tarjeta' or 'Otros conceptos'."""
    first = str(row_values[0] or "").strip().lower()
    if "pago de tarjeta" in first:
        return "pagos"
    if "otros conceptos" in first:
        return "otros"
    if "tarjeta de" in first or "tarjetas incluidas" in first:
        return "tarjeta_header"
    if "total de" in first:
        return "total"
    return None


async def extract_from_excel(excel_bytes: bytes, categories: list[dict]) -> dict:
    """Extract transactions from an Excel bank statement (Santander format)."""
    import io
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(excel_bytes), read_only=True, data_only=True)
    ws = wb.active or wb[wb.sheetnames[0]]

    transactions = []
    current_section = None
    last_date = None
    card_info = ""
    statement_period = ""

    # Detect card info from sheet name
    card_info = ws.title or ""

    for row in ws.iter_rows(values_only=True):
        vals = list(row)
        if not any(v for v in vals):
            continue

        first = str(vals[0] or "").strip()

        # Detect sections
        section = _is_section_header(vals)
        if section:
            current_section = section
            continue

        # Skip header rows
        if _is_header_row(vals):
            continue

        # Skip total rows
        if first.lower().startswith("total de"):
            continue

        # Detect statement period from "Fecha de cierre"
        if first.lower() == "fecha de cierre":
            continue
        if not statement_period and len(vals) >= 2:
            cierre = str(vals[0] or "")
            if "/" in cierre and len(cierre) == 10:
                # Could be a date like 26/03/2026
                try:
                    parts = cierre.split("/")
                    if len(parts) == 3 and len(parts[2]) == 4:
                        statement_period = f"{parts[2]}-{parts[1]}"
                except Exception:
                    pass

        # Skip non-transaction sections
        if current_section in ("otros", "total"):
            continue

        # Parse transaction rows (6 columns: Fecha, Descripción, Cuotas, Comprobante, Monto pesos, Monto dólares)
        if len(vals) < 5:
            continue

        fecha_raw = vals[0]
        descripcion = str(vals[1] or "").strip()
        cuotas = str(vals[2] or "").strip()
        monto_pesos = vals[4] if len(vals) > 4 else None
        monto_dolares = vals[5] if len(vals) > 5 else None

        if not descripcion:
            continue

        # Skip payment/refund entries and administrative entries
        desc_lower = descripcion.lower()
        if any(skip in desc_lower for skip in [
            "su pago en pesos", "transferencia deuda", "aviso importante",
            "movimientos del resumen", "cierres y vencimientos",
        ]):
            continue

        # Handle date (may be empty = same as previous)
        if fecha_raw:
            fecha_str = str(fecha_raw).strip()
            if "/" in fecha_str:
                try:
                    parts = fecha_str.split("/")
                    if len(parts) == 3:
                        d, m, y = parts
                        if len(y) == 4:
                            last_date = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
                except Exception:
                    pass

        if not last_date:
            continue

        # Parse amount
        monto_pesos_val = _parse_ar_money(str(monto_pesos)) if monto_pesos else None
        monto_dolares_val = _parse_ar_money(str(monto_dolares)) if monto_dolares else None

        if monto_pesos_val is not None and monto_pesos_val != 0:
            monto = abs(monto_pesos_val)
            moneda = "ARS"
            tipo = "Ingreso" if monto_pesos_val < 0 else "Gasto"
        elif monto_dolares_val is not None and monto_dolares_val != 0:
            monto = abs(monto_dolares_val)
            moneda = "USD"
            tipo = "Ingreso" if monto_dolares_val < 0 else "Gasto"
        else:
            continue

        # Clean description
        desc_clean = descripcion.strip()
        if cuotas:
            desc_clean = f"{desc_clean} ({cuotas})"

        transactions.append({
            "fecha": last_date,
            "descripcion": desc_clean,
            "monto": round(monto, 2),
            "moneda": moneda,
            "tipo": tipo,
            "categoria_id": None,
            "subcategoria_id": None,
        })

    wb.close()

    # Use AI to suggest categories if we have categories
    if transactions and categories:
        transactions = await _ai_categorize_batch(transactions, categories)

    return {
        "transactions": transactions,
        "statement_period": statement_period,
        "card_or_account": card_info,
    }


async def _ai_categorize_batch(transactions: list[dict], categories: list[dict]) -> list[dict]:
    """Use AI to suggest categories for a batch of transactions."""
    cats_json = _build_categories_json(categories)
    descs = [t["descripcion"] for t in transactions]
    descs_text = "\n".join(f"{i+1}. {d}" for i, d in enumerate(descs))

    prompt = f"""Tengo estas transacciones de un resumen de tarjeta de crédito argentino.
Para cada una, sugerí la categoría y subcategoría más apropiada.

Transacciones:
{descs_text}

Categorías disponibles:
{cats_json}

Respondé SOLO con JSON: {{"suggestions": [{{"index": 1, "categoria_id": <int o null>, "subcategoria_id": <int o null>}}, ...]}}"""

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model="gpt-5.5",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_completion_tokens=2000,
        )
        raw = response.choices[0].message.content or "{}"
        result = json.loads(raw)
        for s in result.get("suggestions", []):
            idx = s.get("index", 0) - 1
            if 0 <= idx < len(transactions):
                transactions[idx]["categoria_id"] = s.get("categoria_id")
                transactions[idx]["subcategoria_id"] = s.get("subcategoria_id")
    except Exception as e:
        logger.warning("AI batch categorization failed: %s", e)

    return transactions


async def parse_statement(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    categories: list[dict],
) -> dict:
    """Dispatch to the right extractor based on file type."""
    fname_lower = filename.lower()
    if mime_type in ("image/jpeg", "image/jpg", "image/png", "image/webp"):
        return await extract_from_image(file_bytes, mime_type, categories)
    elif fname_lower.endswith(".xlsx") or fname_lower.endswith(".xls") or \
         mime_type in ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       "application/vnd.ms-excel"):
        return await extract_from_excel(file_bytes, categories)
    elif mime_type == "application/pdf" or fname_lower.endswith(".pdf"):
        return await extract_from_pdf(file_bytes, categories)
    else:
        return {"transactions": [], "error": f"Formato no soportado: {mime_type}"}
