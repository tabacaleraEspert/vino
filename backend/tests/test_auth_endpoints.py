"""
Integration tests for /api/v1/auth endpoints.

Tests: POST /register, POST /login, GET /me.

The DB session is replaced by a mock (via conftest override) so no real
SQL Server connection is made. Repository functions are patched per test
so we can control what the "DB" returns.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import make_token, make_user_dict

pytestmark = pytest.mark.anyio

BASE = "/api/v1/auth"


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------

class TestRegister:
    async def test_should_create_user_and_return_201_data(self, client):
        user = make_user_dict()
        with patch("app.api.v1.auth.create_user", new_callable=AsyncMock, return_value=user):
            resp = await client.post(f"{BASE}/register", json={
                "username": "testuser",
                "password": "secret123",
            })
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["id"] == user["id"]
        assert body["user"]["nombre"] == user["Nombre"]
        assert "message" in body

    async def test_should_include_apellido_and_email_when_provided(self, client):
        user = make_user_dict()
        with patch("app.api.v1.auth.create_user", new_callable=AsyncMock, return_value=user):
            resp = await client.post(f"{BASE}/register", json={
                "username": "testuser",
                "password": "secret123",
                "apellido": "Garcia",
                "email": "test@example.com",
            })
        assert resp.status_code == 200

    async def test_should_return_400_when_username_is_empty(self, client):
        resp = await client.post(f"{BASE}/register", json={"username": "", "password": "secret123"})
        assert resp.status_code == 400

    async def test_should_return_400_when_password_is_empty(self, client):
        resp = await client.post(f"{BASE}/register", json={"username": "user", "password": ""})
        assert resp.status_code == 400

    async def test_should_return_400_when_password_is_too_short(self, client):
        resp = await client.post(f"{BASE}/register", json={"username": "user", "password": "abc"})
        assert resp.status_code == 400
        assert "6 caracteres" in resp.json()["detail"]

    async def test_should_return_400_when_username_already_exists(self, client):
        with patch(
            "app.api.v1.auth.create_user",
            new_callable=AsyncMock,
            side_effect=ValueError("Ya existe un usuario con nombre 'testuser'"),
        ):
            resp = await client.post(f"{BASE}/register", json={
                "username": "testuser",
                "password": "secret123",
            })
        assert resp.status_code == 400
        assert "Ya existe" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------

class TestLogin:
    async def test_should_return_token_for_valid_credentials(self, client):
        user = make_user_dict(password="secret123")
        with patch("app.api.v1.auth.get_user_by_nombre", new_callable=AsyncMock, return_value=user):
            resp = await client.post(f"{BASE}/login", json={
                "username": "testuser",
                "password": "secret123",
            })
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["user"]["id"] == str(user["id"])
        assert body["user"]["nombre"] == user["Nombre"]

    async def test_should_return_401_for_non_existent_user(self, client):
        with patch("app.api.v1.auth.get_user_by_nombre", new_callable=AsyncMock, return_value=None):
            resp = await client.post(f"{BASE}/login", json={
                "username": "ghost",
                "password": "secret123",
            })
        assert resp.status_code == 401
        assert "incorrectos" in resp.json()["detail"]

    async def test_should_return_401_for_wrong_password(self, client):
        user = make_user_dict(password="secret123")
        with patch("app.api.v1.auth.get_user_by_nombre", new_callable=AsyncMock, return_value=user):
            resp = await client.post(f"{BASE}/login", json={
                "username": "testuser",
                "password": "wrong_password",
            })
        assert resp.status_code == 401

    async def test_should_return_400_when_username_missing(self, client):
        resp = await client.post(f"{BASE}/login", json={"username": "", "password": "secret123"})
        assert resp.status_code == 400

    async def test_should_return_400_when_password_missing(self, client):
        resp = await client.post(f"{BASE}/login", json={"username": "user", "password": ""})
        assert resp.status_code == 400

    async def test_should_strip_whitespace_from_username(self, client):
        """Username with leading/trailing spaces must be stripped before lookup."""
        user = make_user_dict(nombre="testuser", password="secret123")
        with patch("app.api.v1.auth.get_user_by_nombre", new_callable=AsyncMock, return_value=user) as mock_get:
            await client.post(f"{BASE}/login", json={
                "username": "  testuser  ",
                "password": "secret123",
            })
        mock_get.assert_awaited_once_with(mock_get.call_args[0][0], "testuser")


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------

class TestMe:
    async def test_should_return_payload_for_authenticated_user(self, client, auth_headers):
        resp = await client.get(f"{BASE}/me", headers=auth_headers)
        assert resp.status_code == 200
        assert "user" in resp.json()
        assert resp.json()["user"]["sub"] == "42"

    async def test_should_return_401_without_token(self, client):
        resp = await client.get(f"{BASE}/me")
        assert resp.status_code == 401

    async def test_should_return_401_with_invalid_token(self, client):
        resp = await client.get(f"{BASE}/me", headers={"Authorization": "Bearer not.a.token"})
        assert resp.status_code == 401

    async def test_should_return_401_with_malformed_header(self, client):
        resp = await client.get(f"{BASE}/me", headers={"Authorization": "Token abc123"})
        # HTTPBearer with auto_error=False returns None creds -> require_user raises 401
        assert resp.status_code == 401
