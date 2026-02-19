"""
Utilidades de parseo para fechas, períodos y montos.
Usado por views (home summary) y otros módulos que consumen datos de Sheets.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional, Tuple


def parse_period(period: str) -> Tuple[date, date]:
    """
    Parsea period "YYYY-MM" y devuelve (primer_día, último_día) del mes.
    Raises ValueError si el formato es inválido.
    """
    s = (period or "").strip()
    if not s:
        raise ValueError("period es obligatorio")
    parts = s.split("-")
    if len(parts) != 2:
        raise ValueError(f"period debe ser YYYY-MM, recibido: {period}")
    try:
        y, m = int(parts[0]), int(parts[1])
        if m < 1 or m > 12:
            raise ValueError(f"mes inválido: {m}")
        if y < 1900 or y > 2100:
            raise ValueError(f"año inválido: {y}")
        date_from = date(y, m, 1)
        if m == 12:
            date_to = date(y, 12, 31)
        else:
            date_to = date(y, m + 1, 1) - timedelta(days=1)
        return date_from, date_to
    except (ValueError, TypeError) as e:
        if isinstance(e, ValueError) and "inválido" in str(e):
            raise
        raise ValueError(f"period inválido: {period}") from e


def parse_date_flex(value: any) -> Optional[date]:
    """
    Parsea fecha aceptando YYYY-MM-DD o DD/MM/YYYY.
    Para API y payloads flexibles.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    # YYYY-MM-DD
    if re.match(r"^\d{4}-\d{1,2}-\d{1,2}", s):
        parts = s.split("-")
        if len(parts) >= 3:
            try:
                y, m, d = int(parts[0]), int(parts[1]), int(parts[2].split()[0])
                return date(y, m, d)
            except (ValueError, TypeError):
                pass
    # DD/MM/YYYY
    return parse_date_ddmmyyyy(value)


def parse_date_ddmmyyyy(value: any) -> Optional[date]:
    """
    Parsea fecha en formato DD/MM/YYYY (con espacios posibles).
    Ej: "1/12/2025 ", "01/12/2025", "17/02/2026 ", "6/02/2026 0:00:00"
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    parts = s.split("/")
    if len(parts) != 3:
        return None
    try:
        d, m = int(parts[0]), int(parts[1])
        y_str = parts[2].split()[0] if parts[2] else ""
        y = int(y_str) if y_str else 0
        if not y:
            return None
        return date(y, m, d)
    except (ValueError, TypeError):
        return None


def parse_money(value: any) -> float:
    """
    Parsea monto desde string. Soporta:
    - "48,146" -> 48146 (coma como separador de miles)
    - "48146.50" -> 48146.50 (punto decimal)
    - "$ 48.146" -> 48146
    Regla estable: quitar $, espacios, comas; mantener dígitos, punto y guión.
    """
    if value is None:
        return 0.0
    s = str(value).strip().replace("$", "").replace(" ", "").replace(",", "")
    if not s:
        return 0.0
    s = re.sub(r"[^0-9.\-]", "", s)
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


def parse_periodo_mes(mes_anio: str) -> date:
    """
    Parsea mesAño a date (primer día del mes).
    Acepta: "MM/YY" (ej: 12/25), "YYYY-MM" (ej: 2025-12).
    YY < 50 => 20YY, else 19YY.
    Raises ValueError si inválido.
    """
    import re
    s = (mes_anio or "").strip()
    if not s:
        raise ValueError("mesAño es obligatorio")
    # YYYY-MM
    if re.match(r"^\d{4}-\d{1,2}$", s):
        parts = s.split("-")
        y, m = int(parts[0]), int(parts[1])
        if m < 1 or m > 12:
            raise ValueError(f"mes inválido: {m}")
        return date(y, m, 1)
    # MM/YY
    if re.match(r"^(0[1-9]|1[0-2])/\d{2}$", s):
        parts = s.split("/")
        m, yy = int(parts[0]), int(parts[1])
        y = 2000 + yy if yy < 50 else 1900 + yy
        return date(y, m, 1)
    raise ValueError(f"mesAño debe ser MM/YY (ej: 12/25) o YYYY-MM, recibido: {mes_anio}")


def periodo_mes_to_mes_anio(periodo: date | None) -> str:
    """Convierte date (primer día del mes) a "MM/YY"."""
    if periodo is None:
        return ""
    yy = periodo.year % 100
    return f"{periodo.month:02d}/{yy:02d}"


def normalize_mes_anio(s: str) -> str:
    """
    Normaliza mes/año a formato "YYYY-MM".
    Soporta: "2025-10", "10/2025", "10/25", "12/25" (MM/YY).
    """
    if not s or not str(s).strip():
        return ""
    s = str(s).strip()
    # "2025-10" -> ya normalizado
    if re.match(r"^\d{4}-\d{1,2}$", s):
        parts = s.split("-")
        return f"{parts[0]}-{int(parts[1]):02d}"
    # "10/2025" -> MM/YYYY
    if re.match(r"^\d{1,2}/\d{4}$", s):
        parts = s.split("/")
        m, y = int(parts[0]), int(parts[1])
        return f"{y}-{m:02d}"
    # "12/25" o "10/25" -> MM/YY
    if re.match(r"^\d{1,2}/\d{2}$", s):
        parts = s.split("/")
        m, yy = int(parts[0]), int(parts[1])
        y = 2000 + yy if yy < 50 else 1900 + yy
        return f"{y}-{m:02d}"
    return s
