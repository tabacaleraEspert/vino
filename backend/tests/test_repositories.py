"""
Repository-layer unit tests using a fully mocked AsyncSession.

These tests verify the repository functions call the session correctly and
convert ORM objects to dicts as expected — without hitting any real database.

Pattern per test:
1. Configure mock_db.execute() to return a mock result.
2. Build a minimal ORM-like MagicMock to stand in for the real model.
3. Call the repository function.
4. Assert the returned dict shape and any session method calls.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.anyio

USER_ID = 42


# ---------------------------------------------------------------------------
# Helpers to build mock ORM objects
# ---------------------------------------------------------------------------

def _mock_user(user_id: int = USER_ID, nombre: str = "testuser") -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.Nombre = nombre
    u.Apellido = "Garcia"
    u.gmail = "test@example.com"
    u.PasswordHash = "$2b$12$fakehash"
    u.ID_Sheets = ""
    return u


def _mock_categoria(cat_id: int = 1, nombre: str = "Alimentacion") -> MagicMock:
    c = MagicMock()
    c.Id = cat_id
    c.Nombre = nombre
    c.Icon = "🍔"
    c.Color = "#ff5733"
    c.Id_usuario = USER_ID
    return c


def _mock_subcategoria(sub_id: int = 10, cat_id: int = 1) -> MagicMock:
    s = MagicMock()
    s.Id = sub_id
    s.Id_Categoria = cat_id
    s.Nombre_SubCategoria = "Supermercado"
    s.Id_usuario = USER_ID
    return s


def _mock_movimiento(mov_id: int = 100) -> MagicMock:
    m = MagicMock()
    m.Id = mov_id
    m.Id_usuario = USER_ID
    m.Fecha = date(2026, 4, 1)
    m.Timestamp = datetime(2026, 4, 1, 10, 0, 0)
    m.TipoMovimiento = "Gasto"
    m.Moneda = "ARS"
    m.Monto = Decimal("1500.00")
    m.Descripcion = "Carrefour"
    m.Id_Categoria = 1
    m.Id_SubCategoria = 10
    m.ComercioId = None
    m.MedioCarga = "Manual"
    m.CategoriaManual = False
    m.Origen = None
    m.Origen_Id = None
    m.Id_Credito_Debito = None
    m.Id_Medio_Pago_Final = None
    return m


def _mock_regla(regla_id: int = 200) -> MagicMock:
    r = MagicMock()
    r.Id = regla_id
    r.Id_usuario = USER_ID
    r.Patron = "Carrefour"
    r.PatronNorm = "carrefour"
    r.Id_Categoria = 1
    r.Id_SubCategoria = 10
    r.Prioridad = 100
    r.Activa = True
    r.Confianza = "MANUAL"
    r.ActualizadoEn = datetime(2026, 4, 1, 10, 0)
    return r


def _mock_presupuesto(pres_id: int = 300) -> MagicMock:
    p = MagicMock()
    p.Id = pres_id
    p.Id_usuario = USER_ID
    p.PeriodoMes = date(2026, 4, 1)
    p.Id_Categoria = 1
    p.Id_SubCategoria = 10
    p.Monto = Decimal("5000.00")
    return p


def _execute_returning(obj):
    """Return a mock execute result that yields obj from scalar_one_or_none."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = obj
    result.scalar_one.return_value = 1 if obj else 0
    result.scalars.return_value.all.return_value = [obj] if obj else []
    result.first.return_value = _row_with(obj) if obj else None
    result.all.return_value = [_row_with(obj)] if obj else []
    return result


def _row_with(obj, cat_nombre="Alimentacion", sub_nombre="Supermercado"):
    """Simulate a SQLAlchemy Row with labeled columns."""
    row = MagicMock()
    row.__getitem__ = lambda self, i: obj if i == 0 else None
    row.cat_nombre = cat_nombre
    row.sub_nombre = sub_nombre
    row.categoria_nombre = cat_nombre
    row.subcategoria_nombre = sub_nombre
    return row


# ---------------------------------------------------------------------------
# user_repo
# ---------------------------------------------------------------------------

class TestUserRepo:
    async def test_get_user_by_nombre_returns_dict_when_found(self, mock_db):
        from app.repositories.user_repo import get_user_by_nombre
        user = _mock_user()
        result = MagicMock()
        result.scalar_one_or_none.return_value = user
        mock_db.execute = AsyncMock(return_value=result)

        got = await get_user_by_nombre(mock_db, "testuser")
        assert got is not None
        assert got["id"] == USER_ID
        assert got["Nombre"] == "testuser"
        assert "PasswordHash" in got

    async def test_get_user_by_nombre_returns_none_when_not_found(self, mock_db):
        from app.repositories.user_repo import get_user_by_nombre
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        got = await get_user_by_nombre(mock_db, "ghost")
        assert got is None

    async def test_create_user_raises_when_username_exists(self, mock_db):
        from app.repositories.user_repo import create_user
        existing = _mock_user()
        result = MagicMock()
        result.scalar_one_or_none.return_value = existing
        mock_db.execute = AsyncMock(return_value=result)

        with pytest.raises(ValueError, match="Ya existe"):
            await create_user(mock_db, nombre="testuser", password_hash="hash")

    async def test_create_user_adds_to_session_when_new(self, mock_db):
        from app.repositories.user_repo import create_user
        from app.models.user import User

        # Both calls (get_user_by_nombre lookup + any re-fetch) return None / empty
        result_none = MagicMock()
        result_none.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result_none)

        # After flush, the ORM object should have an id set; we simulate that
        # by capturing the added instance and setting its id in flush.
        added_instances = []
        mock_db.add = MagicMock(side_effect=lambda obj: added_instances.append(obj))

        async def _flush():
            if added_instances:
                added_instances[-1].id = 99

        mock_db.flush = AsyncMock(side_effect=_flush)

        # create_user calls get_user_by_nombre (which builds a real select(User))
        # then adds a new User instance and flushes.  The repo then calls
        # _user_to_dict on the ORM object directly — we need a real User instance.
        got = await create_user(mock_db, nombre="newuser", password_hash="$2b$hash")

        assert mock_db.add.call_count == 1
        mock_db.flush.assert_awaited_once()
        added = added_instances[0]
        assert isinstance(added, User)
        assert added.Nombre == "newuser"
        assert got["Nombre"] == "newuser"


# ---------------------------------------------------------------------------
# categoria_repo
# ---------------------------------------------------------------------------

class TestCategoriaRepo:
    async def test_list_categorias_returns_list_of_dicts(self, mock_db):
        from app.repositories.categoria_repo import list_categorias
        cats = [_mock_categoria(1), _mock_categoria(2, "Transporte")]
        result = MagicMock()
        result.scalars.return_value.all.return_value = cats
        mock_db.execute = AsyncMock(return_value=result)

        got = await list_categorias(mock_db, USER_ID)
        assert len(got) == 2
        assert got[0]["id"] == 1
        assert got[1]["nombre"] == "Transporte"

    async def test_get_categoria_returns_none_when_not_found(self, mock_db):
        from app.repositories.categoria_repo import get_categoria
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        got = await get_categoria(mock_db, USER_ID, 999)
        assert got is None

    async def test_create_categoria_adds_and_flushes(self, mock_db):
        from app.repositories.categoria_repo import create_categoria
        result_none = MagicMock()
        result_none.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result_none)

        with patch("app.repositories.categoria_repo.Categoria") as MockCat:
            instance = _mock_categoria()
            MockCat.return_value = instance
            got = await create_categoria(mock_db, USER_ID, nombre="Salud")

        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()
        assert got["nombre"] == "Alimentacion"  # from mock

    async def test_delete_categoria_returns_false_when_not_found(self, mock_db):
        from app.repositories.categoria_repo import delete_categoria
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        deleted = await delete_categoria(mock_db, USER_ID, 999)
        assert deleted is False

    async def test_delete_categoria_returns_true_and_calls_delete(self, mock_db):
        from app.repositories.categoria_repo import delete_categoria
        cat = _mock_categoria()
        result = MagicMock()
        result.scalar_one_or_none.return_value = cat
        mock_db.execute = AsyncMock(return_value=result)

        deleted = await delete_categoria(mock_db, USER_ID, 1)
        assert deleted is True
        mock_db.delete.assert_awaited_once_with(cat)


# ---------------------------------------------------------------------------
# movimiento_repo (_mov_to_dict)
# ---------------------------------------------------------------------------

class TestMovimientoRepoDictConversion:
    """Test the dict converter directly — no DB call needed."""

    def test_mov_to_dict_basic_fields(self):
        from app.repositories.movimiento_repo import _mov_to_dict
        mov = _mock_movimiento()
        result = _mov_to_dict(mov, categoria_nombre="Alimentacion", subcategoria_nombre="Supermercado")
        assert result["id"] == "100"
        assert result["Id"] == 100
        assert result["fecha"] == "2026-04-01"
        assert result["tipo"] == "Gasto"
        assert result["monto"] == 1500.0
        assert result["categoria"] == "Alimentacion"
        assert result["subcategoria"] == "Supermercado"

    def test_mov_to_dict_normalizes_ingreso_tipo(self):
        from app.repositories.movimiento_repo import _mov_to_dict
        mov = _mock_movimiento()
        mov.TipoMovimiento = "ingreso"
        result = _mov_to_dict(mov)
        assert result["tipo"] == "Ingreso"

    def test_mov_to_dict_handles_none_monto(self):
        from app.repositories.movimiento_repo import _mov_to_dict
        mov = _mock_movimiento()
        mov.Monto = None
        result = _mov_to_dict(mov)
        assert result["monto"] == 0.0

    def test_mov_to_dict_handles_none_fecha(self):
        from app.repositories.movimiento_repo import _mov_to_dict
        mov = _mock_movimiento()
        mov.Fecha = None
        mov.Timestamp = None
        result = _mov_to_dict(mov)
        assert result["fecha"] == ""
        assert result["timestamp"] == ""


# ---------------------------------------------------------------------------
# regla_repo
# ---------------------------------------------------------------------------

class TestReglaRepo:
    async def test_create_regla_raises_when_subcategoria_not_found(self, mock_db):
        from app.repositories.regla_repo import create_regla
        result = MagicMock()
        result.scalar_one_or_none.return_value = None  # no subcategoria found
        mock_db.execute = AsyncMock(return_value=result)

        with pytest.raises(ValueError, match="Subcategoría no encontrada"):
            await create_regla(mock_db, USER_ID, patron="X", id_subcategoria=999)

    async def test_delete_regla_returns_false_when_not_found(self, mock_db):
        from app.repositories.regla_repo import delete_regla
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        deleted = await delete_regla(mock_db, USER_ID, 999)
        assert deleted is False

    async def test_resolve_regla_returns_none_for_empty_comercio(self, mock_db):
        from app.repositories.regla_repo import resolve_regla
        result = await resolve_regla(mock_db, USER_ID, "")
        assert result is None
        # Should not call the DB at all for empty input
        mock_db.execute.assert_not_awaited()

    async def test_update_regla_returns_none_when_not_found(self, mock_db):
        from app.repositories.regla_repo import update_regla
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        got = await update_regla(mock_db, USER_ID, 999, patron="X")
        assert got is None


# ---------------------------------------------------------------------------
# presupuesto_repo
# ---------------------------------------------------------------------------

class TestPresupuestoRepo:
    async def test_delete_presupuesto_returns_false_when_not_found(self, mock_db):
        from app.repositories.presupuesto_repo import delete_presupuesto
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        deleted = await delete_presupuesto(mock_db, USER_ID, 999)
        assert deleted is False

    async def test_pres_to_dict_formats_mes_anio(self):
        from app.repositories.presupuesto_repo import _pres_to_dict
        pres = _mock_presupuesto()
        got = _pres_to_dict(pres, "Alimentacion", "Supermercado")
        assert got["mes_anio"] == "04/26"
        assert got["monto"] == 5000.0
        assert got["categoria_id"] == "1"
        assert got["categoria_nombre"] == "Alimentacion"

    async def test_pres_to_dict_handles_none_periodo(self):
        from app.repositories.presupuesto_repo import _pres_to_dict
        pres = _mock_presupuesto()
        pres.PeriodoMes = None
        got = _pres_to_dict(pres, "", "")
        assert got["mes_anio"] == ""
