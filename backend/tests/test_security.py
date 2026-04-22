"""
Unit tests for app.core.security.

Covers:
- create_access_token / decode_token: happy path, expiry, invalid signatures
- hash_password / verify_password: correctness, wrong password, empty hash
- require_user: valid token, missing creds, expired token
- require_master_key: valid key, missing key, wrong key
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    require_master_key,
    require_user,
    verify_password,
)


# ---------------------------------------------------------------------------
# create_access_token / decode_token
# ---------------------------------------------------------------------------

class TestCreateAndDecodeToken:
    def test_should_return_string_token(self):
        token = create_access_token(sub="99")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_should_encode_sub_claim(self):
        token = create_access_token(sub="42")
        payload = decode_token(token)
        assert payload["sub"] == "42"

    def test_should_include_iat_and_exp_claims(self):
        before = int(time.time())
        token = create_access_token(sub="1")
        payload = decode_token(token)
        assert payload["iat"] >= before
        assert payload["exp"] > payload["iat"]

    def test_should_use_custom_expiry_minutes(self):
        token = create_access_token(sub="1", expires_min=1)
        payload = decode_token(token)
        # exp should be roughly 60s from now
        delta = payload["exp"] - payload["iat"]
        assert 55 <= delta <= 65

    def test_should_raise_401_for_expired_token(self):
        # Token that expired immediately
        token = create_access_token(sub="1", expires_min=0)
        # Force expiry by forging a token with exp in the past
        past_payload = {"sub": "1", "iat": int(time.time()) - 120, "exp": int(time.time()) - 60}
        expired_token = jwt.encode(past_payload, settings.JWT_SECRET, algorithm="HS256")
        with pytest.raises(HTTPException) as exc_info:
            decode_token(expired_token)
        assert exc_info.value.status_code == 401
        assert "expirado" in exc_info.value.detail.lower()

    def test_should_raise_401_for_tampered_token(self):
        token = create_access_token(sub="1") + "tampered"
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401

    def test_should_raise_401_for_wrong_secret(self):
        bad_token = jwt.encode({"sub": "1", "exp": int(time.time()) + 3600}, "wrong_secret", algorithm="HS256")
        with pytest.raises(HTTPException) as exc_info:
            decode_token(bad_token)
        assert exc_info.value.status_code == 401

    def test_should_raise_401_for_garbage_string(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_token("not.a.jwt")
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# hash_password / verify_password
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_should_produce_bcrypt_hash_different_from_plain(self):
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"
        assert hashed.startswith("$2b$")

    def test_should_verify_correct_password(self):
        hashed = hash_password("correct_horse")
        assert verify_password("correct_horse", hashed) is True

    def test_should_reject_wrong_password(self):
        hashed = hash_password("correct_horse")
        assert verify_password("wrong_horse", hashed) is False

    def test_should_return_false_for_empty_hash(self):
        assert verify_password("anypassword", "") is False

    def test_should_return_false_for_none_hash(self):
        # None is cast to "" in verify_password guard
        assert verify_password("anypassword", None) is False

    def test_two_hashes_of_same_password_should_differ(self):
        # bcrypt uses random salt
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2
        assert verify_password("same", h1) is True
        assert verify_password("same", h2) is True

    def test_should_handle_unicode_password(self):
        pwd = "clave_ñoña_123"
        hashed = hash_password(pwd)
        assert verify_password(pwd, hashed) is True
        assert verify_password("clave_nona_123", hashed) is False


# ---------------------------------------------------------------------------
# require_user dependency
# ---------------------------------------------------------------------------

class TestRequireUser:
    def _make_creds(self, token: str) -> HTTPAuthorizationCredentials:
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    def test_should_return_payload_for_valid_token(self):
        token = create_access_token(sub="7")
        creds = self._make_creds(token)
        payload = require_user(creds=creds)
        assert payload["sub"] == "7"

    def test_should_raise_401_when_no_credentials(self):
        with pytest.raises(HTTPException) as exc_info:
            require_user(creds=None)
        assert exc_info.value.status_code == 401

    def test_should_raise_401_for_invalid_token(self):
        creds = self._make_creds("garbage.token.here")
        with pytest.raises(HTTPException) as exc_info:
            require_user(creds=creds)
        assert exc_info.value.status_code == 401

    def test_should_raise_401_when_sub_is_missing(self):
        # Forge token without sub claim
        payload_no_sub = {"iat": int(time.time()), "exp": int(time.time()) + 3600}
        token = jwt.encode(payload_no_sub, settings.JWT_SECRET, algorithm="HS256")
        creds = self._make_creds(token)
        with pytest.raises(HTTPException) as exc_info:
            require_user(creds=creds)
        assert exc_info.value.status_code == 401
        assert "identificador" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# require_master_key dependency
# ---------------------------------------------------------------------------

class TestRequireMasterKey:
    def test_should_pass_with_correct_master_key(self):
        # Should not raise
        require_master_key(x_master_key=settings.MASTER_KEY)

    def test_should_raise_401_with_wrong_key(self):
        with pytest.raises(HTTPException) as exc_info:
            require_master_key(x_master_key="wrong_key")
        assert exc_info.value.status_code == 401

    def test_should_raise_401_with_no_key(self):
        with pytest.raises(HTTPException) as exc_info:
            require_master_key(x_master_key=None)
        assert exc_info.value.status_code == 401

    def test_should_raise_401_with_empty_string(self):
        with pytest.raises(HTTPException) as exc_info:
            require_master_key(x_master_key="")
        assert exc_info.value.status_code == 401
