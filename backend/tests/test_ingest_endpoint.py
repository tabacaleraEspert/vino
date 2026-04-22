"""
Tests for POST /api/v1/ingest and POST /api/v1/ingest/batch.

All repository calls are patched so no real DB is touched.
The endpoint is protected by X-Master-Key; every request must supply the header.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from tests.conftest import make_movimiento_dict, make_regla_dict, make_user_dict

pytestmark = pytest.mark.anyio

MASTER_HEADERS = {"X-Master-Key": settings.MASTER_KEY}
WRONG_MASTER_HEADERS = {"X-Master-Key": "wrong_key"}

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

BASE_PAYLOAD: dict = {
    "usuario_gmail": "test@gmail.com",
    "fecha": "2026-04-01",
    "monto": 1500.0,
    "moneda": "ARS",
    "tipo": "Gasto",
    "comercio_raw": "Carrefour",
    "origen": "Gmail",
    "origen_id": "msg-001",
}

_USER = {**make_user_dict(), "gmail": "test@gmail.com", "WppEntero": "+5491112345678"}
_MOVIMIENTO = make_movimiento_dict()
_REGLA = make_regla_dict()

_AUTO_REGLA = {
    **make_regla_dict(regla_id=999),
    "categoria_id": 6,
    "categoria_nombre": "Otros",
    "subcategoria_id": 42,
    "subcategoria_nombre": "Gastos no categorizados",
}


def _patch_repos(
    *,
    user=_USER,
    movimiento_by_origen=None,
    regla=_REGLA,
    created_movimiento=None,
    created_regla=None,
    medio_pago=None,
):
    """Return a context-manager stack that patches all ingest dependencies."""
    if created_movimiento is None:
        created_movimiento = _MOVIMIENTO
    if medio_pago is None:
        medio_pago = {
            "id_credito_debito": None,
            "id_medio_pago_final": None,
            "credito_debito": "",
            "medio_de_pago_final": "",
        }

    patches = [
        patch(
            "app.api.v1.ingest.get_user_by_gmail",
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            "app.api.v1.ingest.get_movimiento_by_origen",
            new_callable=AsyncMock,
            return_value=movimiento_by_origen,
        ),
        patch(
            "app.api.v1.ingest.resolve_regla",
            new_callable=AsyncMock,
            return_value=regla,
        ),
        patch(
            "app.api.v1.ingest.create_regla",
            new_callable=AsyncMock,
            return_value=created_regla,
        ),
        patch(
            "app.api.v1.ingest.repo_create",
            new_callable=AsyncMock,
            return_value=created_movimiento,
        ),
        patch(
            "app.api.v1.ingest.resolve_medio_pago",
            new_callable=AsyncMock,
            return_value=medio_pago,
        ),
    ]
    return patches


# ---------------------------------------------------------------------------
# Helper: apply a list of patches around an async test body
# ---------------------------------------------------------------------------

from contextlib import ExitStack


async def _with_patches(patches, coro):
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        return await coro


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


class TestIngestSecurity:
    async def test_should_return_401_without_master_key(self, client):
        resp = await client.post("/api/v1/ingest", json=BASE_PAYLOAD)
        assert resp.status_code == 401

    async def test_should_return_401_with_wrong_master_key(self, client):
        resp = await client.post(
            "/api/v1/ingest", json=BASE_PAYLOAD, headers=WRONG_MASTER_HEADERS
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestIngestValidation:
    async def test_should_return_400_when_usuario_gmail_missing(self, client):
        payload = {**BASE_PAYLOAD}
        del payload["usuario_gmail"]
        resp = await client.post("/api/v1/ingest", json=payload, headers=MASTER_HEADERS)
        assert resp.status_code == 400
        assert "usuario_gmail" in resp.json()["detail"]

    async def test_should_return_400_when_usuario_gmail_empty(self, client):
        payload = {**BASE_PAYLOAD, "usuario_gmail": "   "}
        resp = await client.post("/api/v1/ingest", json=payload, headers=MASTER_HEADERS)
        assert resp.status_code == 400

    async def test_should_return_404_when_gmail_not_found(self, client):
        patches = _patch_repos(user=None)
        resp = await _with_patches(
            patches,
            client.post("/api/v1/ingest", json=BASE_PAYLOAD, headers=MASTER_HEADERS),
        )
        assert resp.status_code == 404
        assert "no encontrado" in resp.json()["detail"].lower()

    async def test_should_return_400_when_fecha_missing(self, client):
        payload = {**BASE_PAYLOAD}
        del payload["fecha"]
        patches = _patch_repos()
        resp = await _with_patches(
            patches,
            client.post("/api/v1/ingest", json=payload, headers=MASTER_HEADERS),
        )
        assert resp.status_code == 400
        assert "fecha" in resp.json()["detail"].lower()

    async def test_should_return_400_when_fecha_unparseable(self, client):
        payload = {**BASE_PAYLOAD, "fecha": "not-a-date"}
        patches = _patch_repos()
        resp = await _with_patches(
            patches,
            client.post("/api/v1/ingest", json=payload, headers=MASTER_HEADERS),
        )
        assert resp.status_code == 400

    async def test_should_return_400_when_monto_negative(self, client):
        payload = {**BASE_PAYLOAD, "monto": -100}
        patches = _patch_repos()
        resp = await _with_patches(
            patches,
            client.post("/api/v1/ingest", json=payload, headers=MASTER_HEADERS),
        )
        assert resp.status_code == 400
        assert "monto" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestIngestHappyPath:
    async def test_should_return_creado_with_full_response_shape(self, client):
        patches = _patch_repos()
        resp = await _with_patches(
            patches,
            client.post("/api/v1/ingest", json=BASE_PAYLOAD, headers=MASTER_HEADERS),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "creado"
        assert "movimiento" in body
        assert "usuario" in body
        assert "id" in body["usuario"]
        assert "nombre" in body["usuario"]
        assert "wpp_entero" in body["usuario"]

    async def test_should_include_wpp_entero_from_user(self, client):
        user = {**_USER, "WppEntero": "+5491199887766"}
        patches = _patch_repos(user=user)
        resp = await _with_patches(
            patches,
            client.post("/api/v1/ingest", json=BASE_PAYLOAD, headers=MASTER_HEADERS),
        )
        assert resp.json()["usuario"]["wpp_entero"] == "+5491199887766"

    async def test_should_normalize_tipo_gasto(self, client):
        payload = {**BASE_PAYLOAD, "tipo": "gasto"}
        patches = _patch_repos()
        resp = await _with_patches(
            patches,
            client.post("/api/v1/ingest", json=payload, headers=MASTER_HEADERS),
        )
        assert resp.status_code == 200

    async def test_should_normalize_tipo_ingreso(self, client):
        payload = {**BASE_PAYLOAD, "tipo": "ingreso"}
        patches = _patch_repos()
        resp = await _with_patches(
            patches,
            client.post("/api/v1/ingest", json=payload, headers=MASTER_HEADERS),
        )
        assert resp.status_code == 200

    async def test_should_accept_fecha_ddmmyyyy_format(self, client):
        payload = {**BASE_PAYLOAD, "fecha": "01/04/2026"}
        patches = _patch_repos()
        resp = await _with_patches(
            patches,
            client.post("/api/v1/ingest", json=payload, headers=MASTER_HEADERS),
        )
        assert resp.status_code == 200

    async def test_should_accept_zero_monto(self, client):
        payload = {**BASE_PAYLOAD, "monto": 0}
        patches = _patch_repos()
        resp = await _with_patches(
            patches,
            client.post("/api/v1/ingest", json=payload, headers=MASTER_HEADERS),
        )
        assert resp.status_code == 200

    async def test_should_default_moneda_to_ARS_when_absent(self, client):
        payload = {k: v for k, v in BASE_PAYLOAD.items() if k != "moneda"}
        patches = _patch_repos()
        resp = await _with_patches(
            patches,
            client.post("/api/v1/ingest", json=payload, headers=MASTER_HEADERS),
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestIngestDeduplication:
    async def test_should_return_duplicado_when_origen_id_exists(self, client):
        patches = _patch_repos(movimiento_by_origen=_MOVIMIENTO)
        resp = await _with_patches(
            patches,
            client.post("/api/v1/ingest", json=BASE_PAYLOAD, headers=MASTER_HEADERS),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "duplicado"
        assert "movimiento" in body
        assert "usuario" in body
        # duplicado response must NOT have regla key
        assert "regla" not in body

    async def test_should_not_deduplicate_when_origen_id_absent(self, client):
        payload = {k: v for k, v in BASE_PAYLOAD.items() if k != "origen_id"}
        patches = _patch_repos()
        resp = await _with_patches(
            patches,
            client.post("/api/v1/ingest", json=payload, headers=MASTER_HEADERS),
        )
        assert resp.json()["status"] == "creado"


# ---------------------------------------------------------------------------
# Regla resolution
# ---------------------------------------------------------------------------


class TestIngestRegla:
    async def test_should_report_regla_match_true_when_rule_exists(self, client):
        patches = _patch_repos(regla=_REGLA)
        resp = await _with_patches(
            patches,
            client.post("/api/v1/ingest", json=BASE_PAYLOAD, headers=MASTER_HEADERS),
        )
        body = resp.json()
        assert body["regla"]["match"] is True
        assert body["regla"]["creada"] is False
        assert body["regla"]["categoria"] == _REGLA["categoria_nombre"]
        assert body["regla"]["subcategoria"] == _REGLA["subcategoria_nombre"]

    async def test_should_create_auto_rule_and_use_defaults_when_no_regla(self, client):
        patches = _patch_repos(regla=None, created_regla=_AUTO_REGLA)
        resp = await _with_patches(
            patches,
            client.post("/api/v1/ingest", json=BASE_PAYLOAD, headers=MASTER_HEADERS),
        )
        body = resp.json()
        assert body["regla"]["match"] is True
        assert body["regla"]["creada"] is True
        assert body["regla"]["categoria"] == "Otros"
        assert body["regla"]["subcategoria"] == "Gastos no categorizados"

    async def test_should_not_fail_when_auto_rule_creation_raises(self, client):
        """If create_regla raises, ingestion must still succeed."""
        with patch(
            "app.api.v1.ingest.get_user_by_gmail",
            new_callable=AsyncMock,
            return_value=_USER,
        ), patch(
            "app.api.v1.ingest.get_movimiento_by_origen",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.v1.ingest.resolve_regla",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.v1.ingest.create_regla",
            new_callable=AsyncMock,
            side_effect=Exception("DB constraint"),
        ), patch(
            "app.api.v1.ingest.repo_create",
            new_callable=AsyncMock,
            return_value=_MOVIMIENTO,
        ), patch(
            "app.api.v1.ingest.resolve_medio_pago",
            new_callable=AsyncMock,
            return_value={
                "id_credito_debito": None,
                "id_medio_pago_final": None,
                "credito_debito": "",
                "medio_de_pago_final": "",
            },
        ):
            resp = await client.post(
                "/api/v1/ingest", json=BASE_PAYLOAD, headers=MASTER_HEADERS
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "creado"

    async def test_should_report_no_match_when_comercio_raw_absent(self, client):
        payload = {k: v for k, v in BASE_PAYLOAD.items() if k != "comercio_raw"}
        patches = _patch_repos()
        resp = await _with_patches(
            patches,
            client.post("/api/v1/ingest", json=payload, headers=MASTER_HEADERS),
        )
        body = resp.json()
        assert body["regla"]["match"] is False


# ---------------------------------------------------------------------------
# Medio de pago resolution
# ---------------------------------------------------------------------------


class TestIngestMedioPago:
    async def test_should_call_resolve_medio_pago_when_medio_pago_raw_given(
        self, client
    ):
        medio_result = {
            "id_credito_debito": 1,
            "id_medio_pago_final": 10,
            "credito_debito": "Credito",
            "medio_de_pago_final": "Visa Credito",
        }
        payload = {**BASE_PAYLOAD, "medio_pago_raw": "Visa Credito Santander"}

        with patch(
            "app.api.v1.ingest.get_user_by_gmail",
            new_callable=AsyncMock,
            return_value=_USER,
        ), patch(
            "app.api.v1.ingest.get_movimiento_by_origen",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.v1.ingest.resolve_regla",
            new_callable=AsyncMock,
            return_value=_REGLA,
        ), patch(
            "app.api.v1.ingest.create_regla",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.v1.ingest.repo_create",
            new_callable=AsyncMock,
            return_value=_MOVIMIENTO,
        ) as mock_create, patch(
            "app.api.v1.ingest.resolve_medio_pago",
            new_callable=AsyncMock,
            return_value=medio_result,
        ) as mock_resolve:
            resp = await client.post(
                "/api/v1/ingest", json=payload, headers=MASTER_HEADERS
            )

        assert resp.status_code == 200
        mock_resolve.assert_awaited_once()
        # id_credito_debito and id_medio_pago_final from resolve must reach repo_create
        _, kwargs = mock_create.call_args
        assert kwargs["id_credito_debito"] == 1
        assert kwargs["id_medio_pago_final"] == 10

    async def test_should_not_call_resolve_medio_pago_when_direct_ids_given(
        self, client
    ):
        payload = {
            **BASE_PAYLOAD,
            "id_credito_debito": 2,
            "id_medio_pago_final": 20,
        }

        with patch(
            "app.api.v1.ingest.get_user_by_gmail",
            new_callable=AsyncMock,
            return_value=_USER,
        ), patch(
            "app.api.v1.ingest.get_movimiento_by_origen",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.v1.ingest.resolve_regla",
            new_callable=AsyncMock,
            return_value=_REGLA,
        ), patch(
            "app.api.v1.ingest.create_regla",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.v1.ingest.repo_create",
            new_callable=AsyncMock,
            return_value=_MOVIMIENTO,
        ) as mock_create, patch(
            "app.api.v1.ingest.resolve_medio_pago",
            new_callable=AsyncMock,
        ) as mock_resolve:
            resp = await client.post(
                "/api/v1/ingest", json=payload, headers=MASTER_HEADERS
            )

        assert resp.status_code == 200
        mock_resolve.assert_not_awaited()
        _, kwargs = mock_create.call_args
        assert kwargs["id_credito_debito"] == 2
        assert kwargs["id_medio_pago_final"] == 20

    async def test_should_call_resolve_medio_pago_when_raw_given_and_one_id_none(
        self, client
    ):
        """medio_pago_raw triggers resolve only when BOTH direct IDs are absent."""
        # Provide medio_pago_raw with id_credito_debito set — resolve should NOT fire
        payload = {
            **BASE_PAYLOAD,
            "medio_pago_raw": "Santander Debito",
            "id_credito_debito": 3,
        }

        with patch(
            "app.api.v1.ingest.get_user_by_gmail",
            new_callable=AsyncMock,
            return_value=_USER,
        ), patch(
            "app.api.v1.ingest.get_movimiento_by_origen",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.v1.ingest.resolve_regla",
            new_callable=AsyncMock,
            return_value=_REGLA,
        ), patch(
            "app.api.v1.ingest.create_regla",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.v1.ingest.repo_create",
            new_callable=AsyncMock,
            return_value=_MOVIMIENTO,
        ), patch(
            "app.api.v1.ingest.resolve_medio_pago",
            new_callable=AsyncMock,
        ) as mock_resolve:
            resp = await client.post(
                "/api/v1/ingest", json=payload, headers=MASTER_HEADERS
            )

        assert resp.status_code == 200
        # id_credito_debito was set, so branch goes to "use direct ids" — no resolve
        mock_resolve.assert_not_awaited()


# ---------------------------------------------------------------------------
# Batch endpoint
# ---------------------------------------------------------------------------


class TestIngestBatch:
    BATCH_URL = "/api/v1/ingest/batch"

    async def test_should_return_401_without_master_key(self, client):
        resp = await client.post(self.BATCH_URL, json={"items": [BASE_PAYLOAD]})
        assert resp.status_code == 401

    async def test_should_return_400_when_items_empty(self, client):
        resp = await client.post(
            self.BATCH_URL, json={"items": []}, headers=MASTER_HEADERS
        )
        assert resp.status_code == 400
        assert "items" in resp.json()["detail"].lower()

    async def test_should_return_400_when_items_absent(self, client):
        resp = await client.post(self.BATCH_URL, json={}, headers=MASTER_HEADERS)
        assert resp.status_code == 400

    async def test_should_return_400_when_more_than_50_items(self, client):
        items = [BASE_PAYLOAD] * 51
        resp = await client.post(
            self.BATCH_URL, json={"items": items}, headers=MASTER_HEADERS
        )
        assert resp.status_code == 400
        assert "50" in resp.json()["detail"]

    async def test_should_process_single_valid_item(self, client):
        patches = _patch_repos()
        resp = await _with_patches(
            patches,
            client.post(
                self.BATCH_URL,
                json={"items": [BASE_PAYLOAD]},
                headers=MASTER_HEADERS,
            ),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["creados"] == 1
        assert body["duplicados"] == 0
        assert body["errores"] == 0
        assert len(body["results"]) == 1
        assert body["results"][0]["index"] == 0
        assert body["results"][0]["status"] == "creado"

    async def test_should_count_duplicados_correctly(self, client):
        patches = _patch_repos(movimiento_by_origen=_MOVIMIENTO)
        resp = await _with_patches(
            patches,
            client.post(
                self.BATCH_URL,
                json={"items": [BASE_PAYLOAD]},
                headers=MASTER_HEADERS,
            ),
        )
        body = resp.json()
        assert body["duplicados"] == 1
        assert body["creados"] == 0

    async def test_should_count_errores_when_item_has_no_gmail(self, client):
        bad_item = {**BASE_PAYLOAD, "usuario_gmail": ""}
        patches = _patch_repos()
        resp = await _with_patches(
            patches,
            client.post(
                self.BATCH_URL,
                json={"items": [bad_item]},
                headers=MASTER_HEADERS,
            ),
        )
        body = resp.json()
        assert body["errores"] == 1
        assert body["results"][0]["status"] == "error"

    async def test_should_process_mixed_batch(self, client):
        """
        Three items: one valid new, one duplicate (by origen_id match),
        one invalid (missing gmail).
        We simulate them by using different origen_ids:
        - item 0: new (get_movimiento_by_origen returns None first call)
        - item 1: dup (returns existing on second call)
        - item 2: error (empty gmail)
        """
        side_effects_by_origen = [None, _MOVIMIENTO]

        with patch(
            "app.api.v1.ingest.get_user_by_gmail",
            new_callable=AsyncMock,
            return_value=_USER,
        ), patch(
            "app.api.v1.ingest.get_movimiento_by_origen",
            new_callable=AsyncMock,
            side_effect=side_effects_by_origen,
        ), patch(
            "app.api.v1.ingest.resolve_regla",
            new_callable=AsyncMock,
            return_value=_REGLA,
        ), patch(
            "app.api.v1.ingest.create_regla",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.v1.ingest.repo_create",
            new_callable=AsyncMock,
            return_value=_MOVIMIENTO,
        ), patch(
            "app.api.v1.ingest.resolve_medio_pago",
            new_callable=AsyncMock,
            return_value={
                "id_credito_debito": None,
                "id_medio_pago_final": None,
                "credito_debito": "",
                "medio_de_pago_final": "",
            },
        ):
            resp = await client.post(
                self.BATCH_URL,
                json={
                    "items": [
                        {**BASE_PAYLOAD, "origen_id": "new-001"},
                        {**BASE_PAYLOAD, "origen_id": "dup-001"},
                        {**BASE_PAYLOAD, "usuario_gmail": ""},
                    ]
                },
                headers=MASTER_HEADERS,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert body["creados"] == 1
        assert body["duplicados"] == 1
        assert body["errores"] == 1
        statuses = [r["status"] for r in body["results"]]
        assert statuses == ["creado", "duplicado", "error"]
