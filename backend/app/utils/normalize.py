"""
Normalización de texto para matching CONTAINS (reglas por comercio).
"""
from __future__ import annotations

import re
import unicodedata


def normalize_text(s: str) -> str:
    """
    Normaliza texto para matching:
    - upper()
    - trim
    - múltiples espacios -> uno
    - remover caracteres que ensucian (*, -, _, /, ., ,, etc.)
    - remover acentos (opcional)
    """
    if not s or not isinstance(s, str):
        return ""
    t = s.strip().upper()
    # Remover acentos
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    # Remover caracteres que ensucian
    t = re.sub(r"[\*\-_/\.\,\;\:\!\?\'\"]+", " ", t)
    # Múltiples espacios -> uno
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def patron_sugerido(merchant_norm: str, max_chars: int = 15) -> str:
    """
    Deriva patron_sugerido desde merchant_norm para regla AUTO.
    Primeras 1-2 palabras alfabéticas (sin números) o primeros max_chars útiles.
    """
    if not merchant_norm:
        return "SIN_DATOS"
    words = [w for w in merchant_norm.split() if w and w.isalpha()][:2]
    if not words:
        return merchant_norm[:max_chars] if len(merchant_norm) > max_chars else merchant_norm
    result = " ".join(words)
    return result[:max_chars] if len(result) > max_chars else result
