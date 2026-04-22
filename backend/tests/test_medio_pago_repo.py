"""
Tests for resolve_medio_pago in app.repositories.medio_pago_repo.

The function queries the DB via SQLAlchemy AsyncSession.  We mock the
session.execute return value so the catalog is fully controlled by each test.

Catalog row shape (mirrors the SELECT labels used in the function):
  {
      "credito_debito": str,      # e.g. "Credito" / "Debito"
      "id_credito_debito": int,
      "medio_de_pago_final": str, # e.g. "Santander Credito"
      "id_medio_de_pago_final": int,
  }
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.repositories.medio_pago_repo import resolve_medio_pago

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_row(**kwargs) -> SimpleNamespace:
    """Build a namespace that mimics a SQLAlchemy Row with _mapping."""
    return SimpleNamespace(_mapping=kwargs)


def _catalog_entry(
    credito_debito: str,
    id_credito_debito: int,
    medio_de_pago_final: str,
    id_medio_de_pago_final: int,
) -> SimpleNamespace:
    return _make_row(
        credito_debito=credito_debito,
        id_credito_debito=id_credito_debito,
        medio_de_pago_final=medio_de_pago_final,
        id_medio_de_pago_final=id_medio_de_pago_final,
    )


def _make_session(catalog_rows: list) -> AsyncMock:
    """Return a mocked AsyncSession whose execute().all() yields catalog_rows."""
    result = MagicMock()
    result.all.return_value = catalog_rows
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    return session


# Sample catalog entries used across tests
_CREDITO_ROW = _catalog_entry("Credito", 1, "Santander Credito", 101)
_DEBITO_ROW = _catalog_entry("Debito", 2, "Santander Debito", 102)
_BBVA_CRED_ROW = _catalog_entry("Credito", 1, "BBVA Credito", 111)
_BBVA_DEB_ROW = _catalog_entry("Debito", 2, "BBVA Debito", 112)
_MACRO_CRED_ROW = _catalog_entry("Credito", 1, "Macro Credito", 121)
_GALICIA_DEB_ROW = _catalog_entry("Debito", 2, "Galicia Debito", 131)
_MP_ROW = _catalog_entry("Debito", 2, "Mercado Pago", 141)


# ---------------------------------------------------------------------------
# Empty catalog
# ---------------------------------------------------------------------------


class TestResolveWithEmptyCatalog:
    async def test_should_return_all_none_when_catalog_is_empty(self):
        session = _make_session([])
        result = await resolve_medio_pago(session, "Visa Credito Santander")
        assert result["id_credito_debito"] is None
        assert result["id_medio_pago_final"] is None
        assert result["credito_debito"] == ""
        assert result["medio_de_pago_final"] == ""


# ---------------------------------------------------------------------------
# Credit / debit detection
# ---------------------------------------------------------------------------


class TestCredDebitDetection:
    async def test_should_detect_credito_from_text(self):
        session = _make_session([_CREDITO_ROW, _DEBITO_ROW])
        result = await resolve_medio_pago(session, "credito santander")
        assert result["id_credito_debito"] == 1
        assert result["credito_debito"] == "Credito"

    async def test_should_detect_debito_from_text(self):
        session = _make_session([_CREDITO_ROW, _DEBITO_ROW])
        result = await resolve_medio_pago(session, "debito santander")
        assert result["id_credito_debito"] == 2
        assert result["credito_debito"] == "Debito"

    async def test_should_detect_credito_english_spelling(self):
        session = _make_session([_CREDITO_ROW, _DEBITO_ROW])
        result = await resolve_medio_pago(session, "credit card notification")
        assert result["id_credito_debito"] == 1

    async def test_should_detect_debit_english_spelling(self):
        session = _make_session([_CREDITO_ROW, _DEBITO_ROW])
        result = await resolve_medio_pago(session, "debit account")
        assert result["id_credito_debito"] == 2

    async def test_should_detect_credito_with_accent_in_raw_text(self):
        session = _make_session([_CREDITO_ROW, _DEBITO_ROW])
        # "crédito" normalizes to "credito"
        result = await resolve_medio_pago(session, "crédito banco nacion")
        assert result["id_credito_debito"] == 1

    async def test_should_not_detect_cred_deb_when_absent(self):
        session = _make_session([_CREDITO_ROW, _DEBITO_ROW])
        result = await resolve_medio_pago(session, "banco nacion transferencia")
        # No credito/debito keyword → id_credito_debito stays None (or fills from medio match)
        # Here no medio matches either, so must be None
        assert result["id_credito_debito"] is None


# ---------------------------------------------------------------------------
# Medio de pago matching by name
# ---------------------------------------------------------------------------


class TestMedioMatchByName:
    async def test_should_match_santander_in_text(self):
        session = _make_session([_CREDITO_ROW, _DEBITO_ROW])
        result = await resolve_medio_pago(session, "Santander Credito consumo")
        assert result["id_medio_pago_final"] == 101
        assert "santander" in result["medio_de_pago_final"].lower()

    async def test_should_match_bbva_in_text(self):
        # The algorithm compares full catalog name ("bbva credito") as substring of texto.
        # Text must therefore contain the complete normalized name.
        session = _make_session([_BBVA_CRED_ROW, _BBVA_DEB_ROW])
        result = await resolve_medio_pago(session, "BBVA Credito consumo")
        assert result["id_medio_pago_final"] == 111

    async def test_should_match_macro_in_text(self):
        session = _make_session([_MACRO_CRED_ROW])
        result = await resolve_medio_pago(session, "macro credito")
        assert result["id_medio_pago_final"] == 121

    async def test_should_match_mercado_pago_in_text(self):
        session = _make_session([_MP_ROW])
        result = await resolve_medio_pago(session, "mercado pago transferencia")
        assert result["id_medio_pago_final"] == 141

    async def test_should_not_match_when_name_not_in_text(self):
        session = _make_session([_CREDITO_ROW])  # only "Santander Credito"
        result = await resolve_medio_pago(session, "BBVA debito consumo")
        assert result["id_medio_pago_final"] is None

    async def test_should_respect_credito_debito_filter_on_name_match(self):
        """When credito is detected, should not match a debito-only entry."""
        session = _make_session([_DEBITO_ROW, _CREDITO_ROW])
        # text says "credito" AND "santander" — debito row should be skipped
        result = await resolve_medio_pago(session, "santander credito")
        assert result["id_medio_pago_final"] == 101
        assert result["credito_debito"] == "Credito"

    async def test_should_skip_duplicate_medio_names_in_catalog(self):
        """If the same medio_de_pago_final appears twice, match should fire once."""
        dup_row = _catalog_entry("Credito", 1, "Santander Credito", 999)
        session = _make_session([_CREDITO_ROW, dup_row])
        result = await resolve_medio_pago(session, "santander credito")
        # First occurrence wins (id 101), not the duplicate (id 999)
        assert result["id_medio_pago_final"] == 101

    async def test_should_fill_credito_debito_from_matched_medio_when_no_keyword(
        self,
    ):
        """If no credito/debito keyword but medio name matches, cred/deb comes from that catalog row."""
        # _CREDITO_ROW has medio_de_pago_final="Santander Credito" (norm: "santander credito").
        # Text must contain the full name for the substring match to fire.
        session = _make_session([_CREDITO_ROW])
        result = await resolve_medio_pago(session, "santander credito notificacion")
        assert result["id_credito_debito"] == 1
        assert result["credito_debito"] == "Credito"


# ---------------------------------------------------------------------------
# Fallback by from_email
# ---------------------------------------------------------------------------


class TestMedioFallbackByEmail:
    async def test_should_resolve_from_santander_email(self):
        session = _make_session([_CREDITO_ROW, _DEBITO_ROW])
        result = await resolve_medio_pago(
            session, "", from_email="avisos@santander.com.ar"
        )
        assert result["id_medio_pago_final"] is not None
        assert "santander" in result["medio_de_pago_final"].lower()

    async def test_should_resolve_from_bbva_email(self):
        session = _make_session([_BBVA_CRED_ROW, _BBVA_DEB_ROW])
        result = await resolve_medio_pago(
            session, "", from_email="avisos-bbva-ar@bbva.com"
        )
        assert result["id_medio_pago_final"] in (111, 112)

    async def test_should_resolve_from_macro_email(self):
        session = _make_session([_MACRO_CRED_ROW])
        result = await resolve_medio_pago(session, "", from_email="noreply@macro.com")
        assert result["id_medio_pago_final"] == 121

    async def test_should_resolve_from_galicia_email(self):
        session = _make_session([_GALICIA_DEB_ROW])
        result = await resolve_medio_pago(
            session, "", from_email="notificaciones@galicia.com.ar"
        )
        assert result["id_medio_pago_final"] == 131

    async def test_should_resolve_from_mercadopago_email(self):
        session = _make_session([_MP_ROW])
        result = await resolve_medio_pago(
            session, "", from_email="notificacion@mercadopago.com"
        )
        assert result["id_medio_pago_final"] == 141

    async def test_should_resolve_from_mercadolibre_email(self):
        session = _make_session([_MP_ROW])
        result = await resolve_medio_pago(
            session, "", from_email="noreply@mercadolibre.com"
        )
        assert result["id_medio_pago_final"] == 141

    async def test_should_return_none_when_email_domain_unknown(self):
        session = _make_session([_CREDITO_ROW])
        result = await resolve_medio_pago(
            session, "", from_email="info@unknownbank.com"
        )
        assert result["id_medio_pago_final"] is None

    async def test_should_respect_credito_debito_filter_on_email_fallback(self):
        """If credito is already detected, fallback must not pick a debito row."""
        session = _make_session([_BBVA_DEB_ROW, _BBVA_CRED_ROW])
        result = await resolve_medio_pago(
            session, "credito", from_email="avisos-bbva-ar@bbva.com"
        )
        # Credito keyword sets id_credito_debito=1; fallback must use the credito row
        assert result["id_credito_debito"] == 1
        assert result["id_medio_pago_final"] == 111


# ---------------------------------------------------------------------------
# Combined scenarios
# ---------------------------------------------------------------------------


class TestMedioCombined:
    async def test_should_resolve_credito_and_entidad_from_full_text(self):
        session = _make_session([_CREDITO_ROW, _DEBITO_ROW])
        result = await resolve_medio_pago(
            session,
            "Santander Credito",
            from_email="",
            asunto="Compra con tarjeta de credito Santander",
        )
        assert result["id_credito_debito"] == 1
        assert result["id_medio_pago_final"] == 101
        assert result["credito_debito"] == "Credito"
        assert "santander" in result["medio_de_pago_final"].lower()

    async def test_should_prefer_name_match_over_email_fallback(self):
        """Name match fires before email fallback; both point to same banco here."""
        session = _make_session([_CREDITO_ROW, _DEBITO_ROW, _BBVA_CRED_ROW])
        result = await resolve_medio_pago(
            session,
            "Santander debito",
            from_email="avisos-bbva-ar@bbva.com",
        )
        # "Santander" matches by name before email-fallback for bbva runs
        assert "santander" in result["medio_de_pago_final"].lower()

    async def test_should_use_asunto_for_text_matching(self):
        session = _make_session([_CREDITO_ROW, _DEBITO_ROW])
        result = await resolve_medio_pago(
            session,
            "",
            from_email="",
            asunto="Consumo Santander Credito 2500 ARS",
        )
        assert result["id_medio_pago_final"] == 101

    async def test_should_return_empty_result_when_nothing_matches(self):
        session = _make_session([_CREDITO_ROW, _DEBITO_ROW])
        result = await resolve_medio_pago(
            session, "transferencia banco nacion", from_email="noreply@bcra.gob.ar"
        )
        assert result["id_credito_debito"] is None
        assert result["id_medio_pago_final"] is None
        assert result["credito_debito"] == ""
        assert result["medio_de_pago_final"] == ""
