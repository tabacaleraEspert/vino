"""Symmetric encryption for storing sensitive tokens (Gmail refresh tokens)."""
from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is not None:
        return _fernet
    key = settings.GMAIL_TOKEN_KEY
    if not key:
        logger.warning("GMAIL_TOKEN_KEY not set — tokens stored in plaintext (dev only)")
        return None
    from cryptography.fernet import Fernet
    _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_token(plain: str) -> str:
    """Encrypt a token. Falls back to plaintext if no key configured."""
    f = _get_fernet()
    if f is None:
        return plain
    return f.encrypt(plain.encode()).decode()


def decrypt_token(cipher: str) -> str:
    """Decrypt a token. Falls back to returning as-is if no key configured."""
    f = _get_fernet()
    if f is None:
        return cipher
    try:
        return f.decrypt(cipher.encode()).decode()
    except Exception:
        # Might be plaintext from dev — return as-is
        logger.warning("Failed to decrypt token — returning as plaintext")
        return cipher
