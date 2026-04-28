"""
Tests for POST /api/v1/whatsapp/intake and whatsapp_intake service.

Service tests: pure unit tests for detect_command (no mocks needed).
Endpoint tests: patch user_repo and classify_intent so no real DB or OpenAI calls.
"""
from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

import pytest

from contextlib import contextmanager
from app.core.config import settings
from app.services.whatsapp_intake import Intent, classify_intent, detect_command


@pytest.fixture(autouse=True)
def _skip_onboarding():
    """Patch count_gastos so onboarding doesn't trigger in any test."""
    with patch("app.api.v1.whatsapp._count_gastos", new_callable=AsyncMock, return_value=100):
        yield
from tests.conftest import make_user_dict

pytestmark = pytest.mark.anyio

MASTER_HEADERS = {"X-Master-Key": settings.MASTER_KEY}

_USER = {
    **make_user_dict(),
    "WppEntero": "whatsapp:+5491112345678",
    "Whatsapp": "+5491112345678",
}

BASE_PAYLOAD = {
    "From": "whatsapp:+5491112345678",
    "Body": "Gasté 5000 en Carrefour",
    "WaId": "5491112345678",
}


# ===========================================================================
# Service: detect_command (pure unit tests, no mocks)
# ===========================================================================


class TestDetectCommand:
    """detect_command only matches explicit commands — never natural language."""

    # --- WEEKLY_RESUME ---

    def test_weekly_resume_exact(self):
        result = detect_command("Weekly_expenses_resume")
        assert result is not None
        assert result["intent"] == Intent.WEEKLY_RESUME

    def test_weekly_resume_case_insensitive(self):
        result = detect_command("weekly_expenses_resume")
        assert result is not None
        assert result["intent"] == Intent.WEEKLY_RESUME

    def test_weekly_resume_with_whitespace(self):
        result = detect_command("  Weekly_expenses_resume  ")
        assert result is not None
        assert result["intent"] == Intent.WEEKLY_RESUME

    def test_weekly_resume_via_button_payload(self):
        result = detect_command("some other text", button_payload="Weekly_expenses_resume")
        assert result is not None
        assert result["intent"] == Intent.WEEKLY_RESUME

    def test_weekly_resume_short_form(self):
        result = detect_command("weekly_resume")
        assert result is not None
        assert result["intent"] == Intent.WEEKLY_RESUME

    # --- CATEGORIZAR ---

    def test_categorizar_with_number(self):
        result = detect_command("CATEGORIZAR 123")
        assert result is not None
        assert result["intent"] == Intent.CATEGORIZACION
        assert result["command_data"]["movimiento_id"] == 123

    def test_categorizar_lowercase(self):
        result = detect_command("categorizar 456")
        assert result is not None
        assert result["intent"] == Intent.CATEGORIZACION
        assert result["command_data"]["movimiento_id"] == 456

    def test_categorizar_without_number_no_match(self):
        result = detect_command("categorizar")
        assert result is None

    # --- CAMBIAR ---

    def test_cambiar_with_id_and_category(self):
        result = detect_command("CAMBIAR 42 Transporte")
        assert result is not None
        assert result["intent"] == Intent.CATEGORIZACION
        assert result["command_data"]["movimiento_id"] == 42
        assert result["command_data"]["nueva_categoria"] == "Transporte"

    def test_cambiar_without_category_no_match(self):
        result = detect_command("CAMBIAR 42")
        assert result is None

    # --- PRESUPUESTO ---

    def test_presupuesto_with_content(self):
        result = detect_command("PRESUPUESTO: algo importante")
        assert result is not None
        assert result["intent"] == Intent.PRESUPUESTO
        assert result["command_data"]["raw_presupuesto"] == "algo importante"

    def test_presupuesto_no_colon_no_match(self):
        result = detect_command("PRESUPUESTO algo")
        assert result is None

    # --- SUGERENCIAS ---

    def test_sugerencias_with_content(self):
        result = detect_command("SUGERENCIAS: como ahorrar")
        assert result is not None
        assert result["intent"] == Intent.SUGERENCIAS
        assert result["command_data"]["raw_sugerencia"] == "como ahorrar"

    def test_sugerencia_singular(self):
        result = detect_command("sugerencia: tip rapido")
        assert result is not None
        assert result["intent"] == Intent.SUGERENCIAS

    # --- Natural language NEVER matches (goes to AI) ---

    def test_expense_text_is_not_a_command(self):
        """Expense messages are natural language, not commands."""
        assert detect_command("Gasté 5000 en Carrefour") is None

    def test_query_text_is_not_a_command(self):
        """Queries are natural language, not commands."""
        assert detect_command("Cuánto gasté este mes?") is None

    def test_suggestion_text_is_not_a_command(self):
        """Purchase advice questions are natural language, not commands."""
        assert detect_command("Puedo comprarme unas zapatillas de 80k?") is None

    def test_resume_text_is_not_a_command(self):
        """Resume requests in natural language are not commands."""
        assert detect_command("cómo vengo este mes?") is None

    def test_greeting_is_not_a_command(self):
        assert detect_command("hola como andas") is None

    def test_empty_body_no_command(self):
        assert detect_command("") is None

    # --- Button payload priority ---

    def test_button_payload_priority_over_body(self):
        result = detect_command("CATEGORIZAR 999", button_payload="Weekly_expenses_resume")
        assert result is not None
        assert result["intent"] == Intent.WEEKLY_RESUME


# ===========================================================================
# Endpoint: security
# ===========================================================================


class TestWhatsAppIntakeSecurity:
    async def test_returns_401_without_master_key(self, client):
        resp = await client.post("/api/v1/whatsapp/intake", json=BASE_PAYLOAD)
        assert resp.status_code == 401

    async def test_returns_401_with_wrong_master_key(self, client):
        resp = await client.post(
            "/api/v1/whatsapp/intake",
            json=BASE_PAYLOAD,
            headers={"X-Master-Key": "wrong"},
        )
        assert resp.status_code == 401


# ===========================================================================
# Endpoint: user resolution
# ===========================================================================


class TestWhatsAppIntakeUserResolution:
    async def test_returns_404_when_user_not_found(self, client):
        with patch(
            "app.api.v1.whatsapp.get_user_by_wpp",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.post(
                "/api/v1/whatsapp/intake",
                json=BASE_PAYLOAD,
                headers=MASTER_HEADERS,
            )
        assert resp.status_code == 404
        assert "no encontrado" in resp.json()["detail"].lower()


# ===========================================================================
# Endpoint: command detection (no AI call)
# ===========================================================================


class TestWhatsAppIntakeCommands:
    async def test_command_weekly_resume(self, client):
        payload = {**BASE_PAYLOAD, "Body": "Weekly_expenses_resume"}
        with patch(
            "app.api.v1.whatsapp.get_user_by_wpp",
            new_callable=AsyncMock,
            return_value=_USER,
        ):
            resp = await client.post(
                "/api/v1/whatsapp/intake",
                json=payload,
                headers=MASTER_HEADERS,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["intent"] == "WEEKLY_RESUME"
        assert body["command_match"] is True
        assert "user" in body
        assert body["user"]["id"] == _USER["id"]

    async def test_command_categorizar(self, client):
        payload = {**BASE_PAYLOAD, "Body": "CATEGORIZAR 42"}
        with patch(
            "app.api.v1.whatsapp.get_user_by_wpp",
            new_callable=AsyncMock,
            return_value=_USER,
        ):
            resp = await client.post(
                "/api/v1/whatsapp/intake",
                json=payload,
                headers=MASTER_HEADERS,
            )
        body = resp.json()
        assert body["intent"] == "CATEGORIZACION"
        assert body["command_data"]["movimiento_id"] == 42

    async def test_command_presupuesto(self, client):
        payload = {**BASE_PAYLOAD, "Body": "PRESUPUESTO: cuanto tengo"}
        with patch(
            "app.api.v1.whatsapp.get_user_by_wpp",
            new_callable=AsyncMock,
            return_value=_USER,
        ):
            resp = await client.post(
                "/api/v1/whatsapp/intake",
                json=payload,
                headers=MASTER_HEADERS,
            )
        body = resp.json()
        assert body["intent"] == "PRESUPUESTO"
        assert body["command_match"] is True

    async def test_command_via_button_payload(self, client):
        payload = {
            **BASE_PAYLOAD,
            "Body": "texto cualquiera",
            "ButtonPayload": "Weekly_expenses_resume",
        }
        with patch(
            "app.api.v1.whatsapp.get_user_by_wpp",
            new_callable=AsyncMock,
            return_value=_USER,
        ):
            resp = await client.post(
                "/api/v1/whatsapp/intake",
                json=payload,
                headers=MASTER_HEADERS,
            )
        assert resp.json()["intent"] == "WEEKLY_RESUME"


# ===========================================================================
# Endpoint: AI classification
# ===========================================================================


class TestWhatsAppIntakeClassification:
    """Natural language messages are always classified by AI, never by regex."""

    async def test_expense_goes_to_ai(self, client):
        """Expense messages go to AI classification, not regex."""
        payload = {**BASE_PAYLOAD, "Body": "Gasté 5000 en Carrefour"}
        with patch(
            "app.api.v1.whatsapp.get_user_by_wpp",
            new_callable=AsyncMock,
            return_value=_USER,
        ), patch(
            "app.api.v1.whatsapp.classify_intent",
            new_callable=AsyncMock,
            return_value=Intent.DATA,
        ) as mock_classify:
            resp = await client.post(
                "/api/v1/whatsapp/intake",
                json=payload,
                headers=MASTER_HEADERS,
            )
        body = resp.json()
        assert body["intent"] == "DATA"
        assert body["command_match"] is False
        mock_classify.assert_awaited_once()

    async def test_query_goes_to_ai(self, client):
        payload = {**BASE_PAYLOAD, "Body": "Cuanto gasté esta semana?"}
        with patch(
            "app.api.v1.whatsapp.get_user_by_wpp",
            new_callable=AsyncMock,
            return_value=_USER,
        ), patch(
            "app.api.v1.whatsapp.classify_intent",
            new_callable=AsyncMock,
            return_value=Intent.QUERY,
        ) as mock_classify:
            resp = await client.post(
                "/api/v1/whatsapp/intake",
                json=payload,
                headers=MASTER_HEADERS,
            )
        body = resp.json()
        assert body["intent"] == "QUERY"
        assert body["command_match"] is False
        mock_classify.assert_awaited_once()

    async def test_greeting_goes_to_ai(self, client):
        payload = {**BASE_PAYLOAD, "Body": "hola"}
        with patch(
            "app.api.v1.whatsapp.get_user_by_wpp",
            new_callable=AsyncMock,
            return_value=_USER,
        ), patch(
            "app.api.v1.whatsapp.classify_intent",
            new_callable=AsyncMock,
            return_value=Intent.OTHER,
        ) as mock_classify:
            resp = await client.post(
                "/api/v1/whatsapp/intake",
                json=payload,
                headers=MASTER_HEADERS,
            )
        body = resp.json()
        assert body["intent"] == "OTHER"
        assert body["command_match"] is False
        mock_classify.assert_awaited_once()

    async def test_ai_failure_defaults_to_other(self, client):
        payload = {**BASE_PAYLOAD, "Body": "asdfghjk"}
        with patch(
            "app.api.v1.whatsapp.get_user_by_wpp",
            new_callable=AsyncMock,
            return_value=_USER,
        ), patch(
            "app.api.v1.whatsapp.classify_intent",
            new_callable=AsyncMock,
            return_value=Intent.OTHER,
        ):
            resp = await client.post(
                "/api/v1/whatsapp/intake",
                json=payload,
                headers=MASTER_HEADERS,
            )
        assert resp.json()["intent"] == "OTHER"


# ===========================================================================
# Service: classify_intent (unit tests — mock OpenAI)
# ===========================================================================


class TestClassifyIntent:
    """classify_intent only returns DATA, QUERY, SUGERENCIAS, or OTHER."""

    def _mock_openai_response(self, json_content: str):
        """Helper: patch OpenAI to return a specific JSON string."""
        mock_choice = type("C", (), {"message": type("M", (), {"content": json_content})()})()
        mock_response = type("R", (), {"choices": [mock_choice]})()
        return patch(
            "app.services.whatsapp_intake._get_openai_client",
            return_value=type("Client", (), {
                "chat": type("Chat", (), {
                    "completions": type("Completions", (), {
                        "create": AsyncMock(return_value=mock_response),
                    })(),
                })(),
            })(),
        )

    async def test_returns_data(self):
        with self._mock_openai_response('{"tipo": "DATA"}'):
            result = await classify_intent("Gasté 5000 en Carrefour")
        assert result == Intent.DATA

    async def test_returns_query(self):
        with self._mock_openai_response('{"tipo": "QUERY"}'):
            result = await classify_intent("Cuánto gasté ayer?")
        assert result == Intent.QUERY

    async def test_returns_sugerencias(self):
        with self._mock_openai_response('{"tipo": "SUGERENCIAS"}'):
            result = await classify_intent("Puedo comprarme unas zapas?")
        assert result == Intent.SUGERENCIAS

    async def test_returns_other(self):
        with self._mock_openai_response('{"tipo": "OTHER"}'):
            result = await classify_intent("Hola")
        assert result == Intent.OTHER

    async def test_rejects_weekly_resume_from_ai(self):
        """AI should never return WEEKLY_RESUME — that's a command."""
        with self._mock_openai_response('{"tipo": "WEEKLY_RESUME"}'):
            result = await classify_intent("cómo vengo este mes")
        assert result == Intent.OTHER

    async def test_rejects_presupuesto_from_ai(self):
        with self._mock_openai_response('{"tipo": "PRESUPUESTO"}'):
            result = await classify_intent("cómo viene mi presupuesto")
        assert result == Intent.OTHER

    async def test_rejects_categorizacion_from_ai(self):
        with self._mock_openai_response('{"tipo": "CATEGORIZACION"}'):
            result = await classify_intent("recategorizar el último gasto")
        assert result == Intent.OTHER

    async def test_rejects_cat_y_subcats_from_ai(self):
        with self._mock_openai_response('{"tipo": "CAT_Y_SUBCATS"}'):
            result = await classify_intent("qué categorías hay")
        assert result == Intent.OTHER

    async def test_rejects_garbage_from_ai(self):
        with self._mock_openai_response('{"tipo": "BANANA"}'):
            result = await classify_intent("algo raro")
        assert result == Intent.OTHER

    async def test_handles_malformed_json(self):
        with self._mock_openai_response("not json at all"):
            result = await classify_intent("test")
        assert result == Intent.OTHER

    async def test_handles_openai_exception(self):
        with patch(
            "app.services.whatsapp_intake._get_openai_client",
            side_effect=Exception("API down"),
        ):
            result = await classify_intent("test")
        assert result == Intent.OTHER


# ===========================================================================
# Endpoint: response shape
# ===========================================================================


class TestWhatsAppIntakeResponseShape:
    async def test_response_has_all_required_fields(self, client):
        payload = {**BASE_PAYLOAD, "Body": "Weekly_expenses_resume"}
        with patch(
            "app.api.v1.whatsapp.get_user_by_wpp",
            new_callable=AsyncMock,
            return_value=_USER,
        ):
            resp = await client.post(
                "/api/v1/whatsapp/intake",
                json=payload,
                headers=MASTER_HEADERS,
            )
        body = resp.json()
        assert "intent" in body
        assert "command_match" in body
        assert "command_data" in body
        assert "user" in body
        assert "raw_body" in body
        assert "id" in body["user"]
        assert "nombre" in body["user"]
        assert "wpp_entero" in body["user"]

    async def test_raw_body_is_trimmed(self, client):
        payload = {**BASE_PAYLOAD, "Body": "  Weekly_expenses_resume  "}
        with patch(
            "app.api.v1.whatsapp.get_user_by_wpp",
            new_callable=AsyncMock,
            return_value=_USER,
        ):
            resp = await client.post(
                "/api/v1/whatsapp/intake",
                json=payload,
                headers=MASTER_HEADERS,
            )
        assert resp.json()["raw_body"] == "Weekly_expenses_resume"
