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
        max_tokens=4000,
        temperature=0,
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
        max_tokens=4000,
        temperature=0,
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


async def parse_statement(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    categories: list[dict],
) -> dict:
    """Dispatch to the right extractor based on file type."""
    if mime_type in ("image/jpeg", "image/jpg", "image/png", "image/webp"):
        return await extract_from_image(file_bytes, mime_type, categories)
    elif mime_type == "application/pdf" or filename.lower().endswith(".pdf"):
        return await extract_from_pdf(file_bytes, categories)
    else:
        return {"transactions": [], "error": f"Formato no soportado: {mime_type}"}
