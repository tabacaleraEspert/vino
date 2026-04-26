"""Service for identifying unknown merchants using AI + web search."""
from __future__ import annotations

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


_IDENTIFY_PROMPT = """Sos un experto en identificar comercios y razones sociales argentinas.

Te voy a dar el nombre de un comercio tal como aparece en un resumen de tarjeta de crédito o débito argentino.
Tu tarea es identificar qué es ese comercio y sugerir una categoría.

Los nombres suelen ser razones sociales, abreviaciones o nombres comerciales. Ejemplos:
- "AKATAKA" → restaurante/bar
- "MERPAGO*SPOTIFY" → suscripción de streaming
- "YPF ESTACION 1234" → estación de servicio
- "FARMACITY" → farmacia
- "STA MARIA SA" → puede ser muchas cosas, buscá en internet

Las categorías disponibles del usuario son:
{categories_json}

Respondé SOLO con JSON válido:
{{
  "comercio_identificado": "Nombre real o descripción del comercio",
  "rubro": "Restaurante / Supermercado / Farmacia / etc.",
  "confianza": "alta" | "media" | "baja",
  "categoria_id": <ID de la categoría sugerida o null>,
  "subcategoria_id": <ID de la subcategoría sugerida o null>,
  "explicacion": "Breve explicación de por qué"
}}

Si no tenés idea de qué es, devolvé confianza "baja" y categoria_id null.
Si necesitarías buscar en internet para confirmar, decilo en la explicación."""


_WEBSEARCH_PROMPT = """Buscá en internet qué es el comercio "{merchant}" en Argentina.
Puede ser una razón social, nombre de fantasía, o abreviación de tarjeta de crédito.

Respondé SOLO con JSON válido:
{{
  "comercio_identificado": "Nombre real del comercio",
  "rubro": "Tipo de negocio",
  "fuente": "URL o referencia de donde sacaste la info",
  "confianza": "alta" | "media" | "baja"
}}"""


def _build_categories_json(categories: list[dict[str, Any]]) -> str:
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


async def identify_merchant(
    merchant_name: str,
    categories: list[dict[str, Any]],
    use_web_search: bool = True,
) -> dict[str, Any]:
    """
    Identify an unknown merchant using AI, optionally with web search.

    Flow:
    1. Ask GPT to identify based on its knowledge
    2. If confidence is low and web_search enabled, search the web
    3. Combine results
    """
    client = _get_client()
    cats_json = _build_categories_json(categories)

    # Step 1: AI identification
    prompt = _IDENTIFY_PROMPT.replace("{categories_json}", cats_json)
    try:
        response = await client.chat.completions.create(
            model="gpt-5.5",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Comercio: {merchant_name}"},
            ],
            response_format={"type": "json_object"},
            max_tokens=200,
            temperature=0,
        )
        raw = response.choices[0].message.content or "{}"
        result = json.loads(raw)
    except Exception as e:
        logger.error("Merchant identification failed for '%s': %s", merchant_name, e)
        return {
            "comercio_identificado": merchant_name,
            "rubro": "Desconocido",
            "confianza": "baja",
            "categoria_id": None,
            "subcategoria_id": None,
            "explicacion": f"Error al identificar: {e}",
            "web_search_used": False,
        }

    # Step 2: Web search if confidence is low
    web_result = None
    if use_web_search and result.get("confianza") == "baja":
        try:
            ws_response = await client.chat.completions.create(
                model="gpt-5.5",
                messages=[
                    {"role": "user", "content": _WEBSEARCH_PROMPT.format(merchant=merchant_name)},
                ],
                response_format={"type": "json_object"},
                max_tokens=200,
                temperature=0,
                # Use web search tool if available
                tools=[{"type": "web_search_preview"}],
            )
            ws_raw = ws_response.choices[0].message.content or "{}"
            web_result = json.loads(ws_raw)
        except Exception as e:
            # Web search not available or failed — that's OK, we have the AI result
            logger.info("Web search failed for '%s': %s", merchant_name, e)

    # Combine results
    if web_result and web_result.get("confianza") in ("alta", "media"):
        result["comercio_identificado"] = web_result.get("comercio_identificado", result.get("comercio_identificado", ""))
        result["rubro"] = web_result.get("rubro", result.get("rubro", ""))
        result["confianza"] = web_result.get("confianza", "media")
        result["explicacion"] = (result.get("explicacion", "") + f" (web: {web_result.get('fuente', '')})").strip()
        result["web_search_used"] = True
    else:
        result["web_search_used"] = False

    return result


async def identify_and_suggest_category(
    merchant_name: str,
    categories: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Convenience wrapper that returns a clean result for the UI.
    """
    result = await identify_merchant(merchant_name, categories, use_web_search=True)

    cat_id = result.get("categoria_id")
    sub_id = result.get("subcategoria_id")

    # Find names
    cat_name = ""
    sub_name = ""
    if cat_id:
        for c in categories:
            if c.get("id") == cat_id:
                cat_name = c.get("nombre", "")
                if sub_id:
                    for s in c.get("subcategorias", []):
                        if s.get("id") == sub_id:
                            sub_name = s.get("nombre", "")
                break

    return {
        "merchant_raw": merchant_name,
        "merchant_identified": result.get("comercio_identificado", merchant_name),
        "rubro": result.get("rubro", ""),
        "confianza": result.get("confianza", "baja"),
        "categoria_id": cat_id,
        "categoria_nombre": cat_name,
        "subcategoria_id": sub_id,
        "subcategoria_nombre": sub_name,
        "explicacion": result.get("explicacion", ""),
        "web_search_used": result.get("web_search_used", False),
    }
