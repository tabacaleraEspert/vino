"""Service for extracting transactions from bank statements using OpenAI."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
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


_MONTH_MAP = {
    "ene": "01", "enero": "01", "feb": "02", "febrero": "02",
    "mar": "03", "marzo": "03", "abr": "04", "abril": "04",
    "may": "05", "mayo": "05", "jun": "06", "junio": "06",
    "jul": "07", "julio": "07", "ago": "08", "agosto": "08",
    "set": "09", "setiem": "09", "sep": "09", "septiem": "09",
    "oct": "10", "octubre": "10", "nov": "11", "noviem": "11",
    "dic": "12", "diciem": "12",
}

# Regex for Santander PDF transaction lines
# Examples:
#   25 Octubre 02 061353 *  NIKE ALCORTA                C.04/06     17.499,83
#   06 888689    OPENAI *CHATGPT  in1SfLrfCUSD       20,00                    20,00
#   02 000071 *  THE KOOPLES                 C.04/06     30.500,00
_SANTANDER_TX_RE = re.compile(
    r"^\s*(?:(\d{1,2})\s+([A-Za-záéíóú]+)\.?\s+)?"  # optional: day + month name
    r"(\d{1,2})\s+"                                    # day of transaction
    r"(\d{5,6})\s*[*K ]?\s*"                           # comprobante number + type
    r"(.+?)"                                           # description (greedy but trimmed)
    r"(?:\s+C\.(\d{2}/\d{2}))?"                        # optional cuotas C.XX/XX
    r"\s+"                                             # separator
    r"([\d.,]+(?:-)?)"                                 # amount (may end with -)
    r"\s*$"
)


def _parse_santander_pdf_text(full_text: str) -> dict:
    """Parse Santander Visa PDF text format into transactions."""
    lines = full_text.split("\n")

    transactions = []
    current_month_str = ""  # "01" for Enero
    current_year = ""       # "26" or "2026"
    statement_period = ""
    card_info = "Visa Santander"
    last_date = ""

    # Skip patterns
    skip_patterns = [
        "SALDO ANTERIOR", "SU PAGO EN PESOS", "TRANSFERENCIA DEUDA",
        "IMPUESTO DE SELLOS", "INTERESES FINANC", "DB IVA", "IIBB PERCEP",
        "IVA RG 4240", "DB.RG 5617", "Tarjeta", "Total Consumos",
        "Plan V:", "fijas su saldo", "cuotas de $", "TNA:", "CFTEA",
    ]

    # Extract CIERRE date and VENCIMIENTO for year reference
    for line in lines:
        # "CIERRE  29 Ene 26 VENCIMIENTO 06 Feb 26"
        m = re.search(r"CIERRE\s+(\d{1,2})\s+(\w+)\s+(\d{2,4})", line)
        if m:
            day, mon, yr = m.group(1), m.group(2).lower(), m.group(3)
            for key, val in _MONTH_MAP.items():
                if mon.startswith(key):
                    current_year = yr if len(yr) == 4 else f"20{yr}"
                    statement_period = f"{current_year}-{val}"
                    break
            break
        # Also try "VENCIMIENTO DD Mes YY" format
        m = re.search(r"VENCIMIENTO\s+(\d{1,2})\s+(\w+)\s+(\d{2,4})", line)
        if m:
            day, mon, yr = m.group(1), m.group(2).lower(), m.group(3)
            for key, val in _MONTH_MAP.items():
                if mon.startswith(key):
                    current_year = yr if len(yr) == 4 else f"20{yr}"
                    statement_period = f"{current_year}-{val}"
                    break
            break

    if not current_year:
        # Try extracting from filename or default
        current_year = "2026"

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Skip boilerplate and non-transaction lines
        if any(skip in line for skip in skip_patterns):
            continue

        # Detect month headers like "25 Octubre", "26 Enero", "25 Setiem."
        month_header = re.match(r"^(\d{1,2})\s+([A-Za-záéíóú]+)\.?\s+(\d{1,2})\s", line)
        if month_header:
            month_name = month_header.group(2).lower()
            for key, val in _MONTH_MAP.items():
                if month_name.startswith(key):
                    current_month_str = val
                    break
            # Adjust year: if month > current statement month, it's previous year
            if statement_period and current_month_str:
                stmt_month = int(statement_period.split("-")[1])
                tx_month = int(current_month_str)
                if tx_month > stmt_month:
                    tx_year = str(int(current_year) - 1)
                else:
                    tx_year = current_year
            else:
                tx_year = current_year

        # Try to parse as transaction
        # Simplified: look for comprobante pattern (5-6 digits followed by * or K)
        tx_match = re.match(
            r"^\s*(?:\d{1,2}\s+[A-Za-záéíóú]+\.?\s+)?"  # optional month header
            r"(\d{1,2})\s+"                               # day
            r"(\d{5,6})\s*([*K ]?)\s*"                    # comprobante + type
            r"(.+?)$",                                     # rest of line
            line
        )

        if not tx_match:
            continue

        day = tx_match.group(1).zfill(2)
        desc_and_amount = tx_match.group(4).strip()

        if not current_month_str:
            continue

        # Determine year for this transaction
        if statement_period:
            stmt_month = int(statement_period.split("-")[1])
            tx_month = int(current_month_str)
            tx_year = str(int(current_year) - 1) if tx_month > stmt_month else current_year
        else:
            tx_year = current_year

        fecha = f"{tx_year}-{current_month_str}-{day}"

        # Parse description and amounts from the rest
        # The amounts are at the end, separated by spaces
        # Pattern: DESCRIPTION [C.XX/XX] [USD_AMOUNT] PESOS_AMOUNT [USD_AMOUNT]

        # Try to extract cuotas
        cuotas = ""
        cuotas_match = re.search(r"C\.(\d{2}/\d{2,3})", desc_and_amount)
        if cuotas_match:
            cuotas = cuotas_match.group(1)

        # Extract amounts (numbers with dots and commas at end of line)
        # Amounts can be: 17.499,83 or 20,00 or 2,99 or 133.309,66
        amounts = re.findall(r"(\d[\d.]*,\d{2}-?)", desc_and_amount)

        if not amounts:
            continue

        # Clean description: remove amounts, cuotas, USD markers, reference codes
        desc_clean = desc_and_amount
        for amt in amounts:
            desc_clean = desc_clean.replace(amt, "")
        desc_clean = re.sub(r"C\.\d{2}/\d{2,3}", "", desc_clean)
        desc_clean = re.sub(r"\bUSD\b", "", desc_clean)
        # Remove long alphanumeric reference codes (e.g., in1SfLrfC, MTZ476WY1, hLhTMW5nA)
        # but keep actual names — only remove if it looks like a hash (mixed case + digits)
        desc_clean = re.sub(r"\b[a-zA-Z0-9]*\d+[a-zA-Z]+[a-zA-Z0-9]*\b", "", desc_clean)
        # Remove long number sequences like 000000041700043, 300070577571001
        desc_clean = re.sub(r"\b\d{10,}\b", "", desc_clean)
        desc_clean = re.sub(r"\s+", " ", desc_clean).strip()

        if not desc_clean or len(desc_clean) < 2:
            continue

        if cuotas:
            desc_clean = f"{desc_clean} ({cuotas})"

        # Determine if USD or ARS
        has_usd = "USD" in desc_and_amount

        # Parse the main amount
        if has_usd and len(amounts) >= 1:
            # USD transaction - typically the last amount is USD
            amount_str = amounts[-1]
            monto = _parse_santander_amount(amount_str)
            moneda = "USD"
        else:
            # ARS transaction
            amount_str = amounts[-1]
            monto = _parse_santander_amount(amount_str)
            moneda = "ARS"

        if monto is None or monto == 0:
            continue

        is_negative = amount_str.endswith("-")
        tipo = "Ingreso" if is_negative else "Gasto"

        transactions.append({
            "fecha": fecha,
            "descripcion": desc_clean,
            "monto": round(abs(monto), 2),
            "moneda": moneda,
            "tipo": tipo,
            "categoria_id": None,
            "subcategoria_id": None,
        })

    return {
        "transactions": transactions,
        "statement_period": statement_period,
        "card_or_account": card_info,
    }


def _parse_santander_amount(s: str) -> float | None:
    """Parse Santander amount: 17.499,83 or 2,99 or 133.309,66-"""
    s = s.strip().rstrip("-")
    if not s:
        return None
    # Santander uses dots for thousands, comma for decimals
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


async def extract_from_pdf(pdf_bytes: bytes, categories: list[dict]) -> dict:
    """Extract transactions from a PDF. Detects Santander format, falls back to AI."""
    from PyPDF2 import PdfReader
    import io

    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)

    full_text = "\n".join(pages_text)

    if len(full_text.strip()) < 100:
        return {
            "transactions": [],
            "error": "El PDF parece ser escaneado. Probá subiendo una foto o screenshot del extracto.",
        }

    # Detect Santander format
    is_santander = "Santander" in full_text and ("VISA" in full_text or "RESUMEN DE CUENTA" in full_text)

    if is_santander:
        result = _parse_santander_pdf_text(full_text)
        # AI categorization
        if result["transactions"] and categories:
            result["transactions"] = await _ai_categorize_batch(result["transactions"], categories)
        return result

    # Generic: send to AI
    return await extract_from_text(full_text, categories)


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
    """Use AI to suggest categories for a batch of transactions, with confidence levels."""
    cats_json = _build_categories_json(categories)
    descs = [t["descripcion"] for t in transactions]
    descs_text = "\n".join(f"{i+1}. {d}" for i, d in enumerate(descs))

    prompt = f"""Sos un experto en identificar comercios argentinos de resúmenes de tarjeta de crédito.
Para cada transacción, identificá qué comercio es y sugerí la categoría más apropiada.

Los nombres pueden ser razones sociales, abreviaciones o nombres de fantasía. Ejemplos:
- "Nike alcorta" → tienda Nike en Alcorta Shopping → Ropa
- "Merpago*spotify" → Spotify vía MercadoPago → Suscripciones/Streaming
- "YPF ESTACION" → estación de servicio → Transporte/Combustible
- "Disney plus" → streaming → Entretenimiento/Streaming
- "Apple.com/bill" → suscripción Apple → Suscripciones

Transacciones:
{descs_text}

Categorías disponibles:
{cats_json}

Para cada transacción respondé con:
- index: número de la transacción (1-based)
- comercio_identificado: nombre real/legible del comercio
- categoria_id: ID de la categoría sugerida (int o null)
- subcategoria_id: ID de la subcategoría sugerida (int o null)
- confianza: "alta" si estás seguro, "media" si es probable, "baja" si no sabés

Respondé SOLO JSON: {{"suggestions": [...]}}"""

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model="gpt-5.5",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_completion_tokens=4000,
        )
        raw = response.choices[0].message.content or "{}"
        result = json.loads(raw)
        for s in result.get("suggestions", []):
            idx = s.get("index", 0) - 1
            if 0 <= idx < len(transactions):
                transactions[idx]["categoria_id"] = s.get("categoria_id")
                transactions[idx]["subcategoria_id"] = s.get("subcategoria_id")
                transactions[idx]["confianza"] = s.get("confianza", "baja")
                if s.get("comercio_identificado"):
                    transactions[idx]["comercio_identificado"] = s["comercio_identificado"]
    except Exception as e:
        logger.error("AI batch categorization failed: %s", e, exc_info=True)

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
