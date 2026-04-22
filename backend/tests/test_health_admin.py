"""
Tests for:
- GET  /api/v1/health
- POST /api/v1/admin/impersonate
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from tests.conftest import make_user_dict

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealth:
    async def test_should_return_ok_and_version(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["version"] == settings.APP_VERSION

    async def test_should_not_require_auth(self, client):
        """Health endpoint must be publicly accessible."""
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Admin impersonate endpoint
# ---------------------------------------------------------------------------

class TestAdminImpersonate:
    MASTER_HEADER = {"X-Master-Key": settings.MASTER_KEY}
    WRONG_MASTER_HEADER = {"X-Master-Key": "wrong_key"}

    async def test_should_return_token_for_existing_user(self, client):
        user = make_user_dict()
        with patch("app.api.v1.admin.get_user_by_nombre", new_callable=AsyncMock, return_value=user):
            resp = await client.post(
                "/api/v1/admin/impersonate",
                json={"username": "testuser"},
                headers=self.MASTER_HEADER,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_should_return_404_for_non_existent_user(self, client):
        with patch("app.api.v1.admin.get_user_by_nombre", new_callable=AsyncMock, return_value=None):
            resp = await client.post(
                "/api/v1/admin/impersonate",
                json={"username": "ghost"},
                headers=self.MASTER_HEADER,
            )
        assert resp.status_code == 404

    async def test_should_return_401_without_master_key(self, client):
        resp = await client.post(
            "/api/v1/admin/impersonate",
            json={"username": "testuser"},
        )
        assert resp.status_code == 401

    async def test_should_return_401_with_wrong_master_key(self, client):
        resp = await client.post(
            "/api/v1/admin/impersonate",
            json={"username": "testuser"},
            headers=self.WRONG_MASTER_HEADER,
        )
        assert resp.status_code == 401
