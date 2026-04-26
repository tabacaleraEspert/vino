"""Service for identifying unknown merchants using AI + web search."""
from __future__ import annotations

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


_IDENTIFY_PROMPT = """Sos un experto en identificar comercios y razones sociales argentinas.

Te voy a dar el nombre de un comercio tal como aparece en un resumen de tarjeta de crédito o débito argentino.
Tu tarea es identificar qué es ese comercio y sugerir una categoría.

Los nombres suelen ser razones sociales, abreviaciones o nombres comerciales. Ejemplos:
- "AKATAKA" → restaurante/bar
- "MERPAGO*SPOTIFY" → suscripción de streaming
- "YPF ESTACION 1234" → estación de servicio
- "FARMACITY" → farmacia
- "STA MARIA SA" → puede ser muchas cosas

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

Si no tenés idea de qué es, devolvé confianza "baja" y categoria_id null."""


_WEBSEARCH_PROMPT = """Necesito identificar qué comercio o empresa es "{merchant}" en Argentina.
Puede ser una razón social, CUIT, nombre de fantasía, o abreviación que aparece en un resumen de tarjeta de crédito.
Si es un CUIT/CUIL, buscalo en internet para saber a quién pertenece.

Decime qué encontraste: nombre del comercio, rubro/tipo de negocio, y una referencia."""


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


def _extract_json(text: str) -> dict:
    """Extract JSON from text that may contain markdown or extra content."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from ```json blocks
    m = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Try finding first { ... }
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {}


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
            max_completion_tokens=500,
        )
        raw = response.choices[0].message.content or "{}"
        result = _extract_json(raw)
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
    web_info = None
    if use_web_search and result.get("confianza") in ("baja", None):
        try:
            ws_response = await client.responses.create(
                model="gpt-5.5",
                tools=[{"type": "web_search_preview"}],
                input=_WEBSEARCH_PROMPT.format(merchant=merchant_name),
            )
            # Extract text from response
            ws_text = ""
            for item in ws_response.output:
                if hasattr(item, "content"):
                    for block in item.content:
                        if hasattr(block, "text"):
                            ws_text += block.text
            if ws_text:
                web_info = ws_text
                logger.info("Web search result for '%s': %s", merchant_name, ws_text[:200])
        except Exception as e:
            logger.info("Web search failed for '%s': %s", merchant_name, e)

    # Step 3: If we got web results, re-ask GPT to classify with that info
    if web_info:
        try:
            reclassify_prompt = f"""Basándote en esta información de internet sobre el comercio "{merchant_name}":

{web_info}

Las categorías disponibles son:
{cats_json}

Respondé SOLO JSON:
{{"comercio_identificado": "nombre", "rubro": "tipo", "confianza": "alta|media|baja", "categoria_id": <int o null>, "subcategoria_id": <int o null>, "explicacion": "breve"}}"""

            re_response = await client.chat.completions.create(
                model="gpt-5.5",
                messages=[{"role": "user", "content": reclassify_prompt}],
                response_format={"type": "json_object"},
                max_completion_tokens=500,
            )
            re_raw = re_response.choices[0].message.content or "{}"
            web_result = _extract_json(re_raw)
            if web_result.get("comercio_identificado"):
                result = web_result
                result["web_search_used"] = True
                result["explicacion"] = (result.get("explicacion", "") or "") + " (verificado con búsqueda web)"
        except Exception as e:
            logger.info("Re-classification after web search failed: %s", e)

    if "web_search_used" not in result:
        result["web_search_used"] = False

    return result


async def identify_and_suggest_category(
    merchant_name: str,
    categories: list[dict[str, Any]],
) -> dict[str, Any]:
    """Convenience wrapper that returns a clean result for the UI."""
    result = await identify_merchant(merchant_name, categories, use_web_search=True)

    cat_id = result.get("categoria_id")
    sub_id = result.get("subcategoria_id")

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
