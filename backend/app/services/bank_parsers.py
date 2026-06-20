"""
Parsers determinísticos (regex) para templates de mail bancarios conocidos.

Cada parser sabe leer UN template fijo de UN banco. Si el texto no matchea
el patrón esperado, devuelve None y el caller debe caer a GPT como fallback
(email_expense_extractor.py).

Por qué regex y no IA acá: dentro de un mismo banco + mismo asunto, el
template es siempre igual (mismo orden de campos), así que es más barato
y más confiable parsearlo con código que pedirle a un LLM que "adivine".
"""
from __future__ import annotations

import re
from typing import Any


def _parse_monto_ar(monto_str: str) -> float:
    """Convierte '25.000,00' (formato AR) a 25000.0."""
    return float(monto_str.replace(".", "").replace(",", "."))


# ---------------------------------------------------------------------------
# BBVA — compra con tarjeta (débito o crédito)
# Asuntos: "Nueva compra", "Compra aprobada"
# Template: ...<fecha DD/MM/YYYY>...<comercio>...<ARS|USD><monto>...
# ---------------------------------------------------------------------------

_BBVA_COMPRA_RE = re.compile(
    r"(\d{2}/\d{2}/\d{4})\s*(.+?)\s*(ARS|USD)\s*([\d.,]+)",
)
_BBVA_TARJETA_RE = re.compile(
    r"tarjeta de (d[eé]bito|cr[eé]dito)\s*(\w+)?\s*terminada en (\d+)",
    re.IGNORECASE,
)


def parse_bbva_compra(subject: str, body_text: str) -> dict[str, Any] | None:
    m = _BBVA_COMPRA_RE.search(body_text)
    if not m:
        return None

    fecha_raw, comercio, moneda, monto_str = m.groups()
    dd, mm, yyyy = fecha_raw.split("/")

    tarjeta_m = _BBVA_TARJETA_RE.search(body_text)
    if tarjeta_m:
        tipo_tarjeta, marca, _terminacion = tarjeta_m.groups()
        tipo_tarjeta = "Débito" if "eb" in tipo_tarjeta.lower() else "Crédito"
        medio_de_pago = f"{(marca or '').strip()} {tipo_tarjeta} BBVA".strip()
    else:
        medio_de_pago = "BBVA"

    return {
        "monto": _parse_monto_ar(monto_str),
        "moneda": moneda,
        "comercio_raw": comercio.strip(),
        "descripcion": f"Compra en {comercio.strip()}",
        "tipo": "Gasto",
        "medio_de_pago": medio_de_pago,
        "fecha": f"{yyyy}-{mm}-{dd}",
        "datos_completos": True,
    }


# ---------------------------------------------------------------------------
# BBVA — transferencia enviada
# Asuntos: "Realizaste una transferencia"
# Template: tabla con labels fijos (Destinatario, CBU, CUIL, Motivo, Importe,
# Fecha y hora, Número de referencia). El texto aparece DOS veces (versión
# desktop + mobile del mismo email responsive) — nos quedamos con la primera.
# ---------------------------------------------------------------------------

_BBVA_TRANSF_FECHA_RE = re.compile(r"(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}:\d{2})")
_BBVA_TRANSF_DESTINATARIO_RE = re.compile(
    r"Destinatario\s+Fecha y hora\s+(.+?)\s+\d{2}/\d{2}/\d{4}"
)
_BBVA_TRANSF_MOTIVO_RE = re.compile(
    r"CUIL\s+Motivo\s+\d+\s+(.+?)\s+Importe"
)
_BBVA_TRANSF_IMPORTE_RE = re.compile(r"Importe\s+\$\s*([\d.,]+)")


def parse_bbva_transferencia_enviada(subject: str, body_text: str) -> dict[str, Any] | None:
    fecha_m = _BBVA_TRANSF_FECHA_RE.search(body_text)
    importe_m = _BBVA_TRANSF_IMPORTE_RE.search(body_text)
    if not fecha_m or not importe_m:
        return None

    dest_m = _BBVA_TRANSF_DESTINATARIO_RE.search(body_text)
    motivo_m = _BBVA_TRANSF_MOTIVO_RE.search(body_text)

    destinatario = dest_m.group(1).strip() if dest_m else ""
    motivo = motivo_m.group(1).strip() if motivo_m else ""
    dd, mm, yyyy = fecha_m.group(1).split("/")

    descripcion = f"Transferencia a {destinatario}" if destinatario else "Transferencia enviada"
    if motivo and motivo.upper() != "VARIOS":
        descripcion += f" ({motivo})"

    return {
        "monto": _parse_monto_ar(importe_m.group(1)),
        "moneda": "ARS",
        "comercio_raw": destinatario,
        "descripcion": descripcion,
        "tipo": "Gasto",
        "medio_de_pago": "Transferencia BBVA",
        "fecha": f"{yyyy}-{mm}-{dd}",
        "datos_completos": True,
    }


# ---------------------------------------------------------------------------
# BBVA — transferencia inmediata debitada (formato nuevo, vía CVU/CUIT, sin nombre)
# Asuntos: "...AVISO TRANSFERENCIA INMEDIATA DEBITADA"
# Template: filas Fecha / Número cuenta / CVU destino / CUIT destino / Importe
# ---------------------------------------------------------------------------

_BBVA_DEBITADA_FECHA_RE = re.compile(r"Fecha\s*(\d{2}/\d{2}/\d{4})")
_BBVA_DEBITADA_CUIT_RE = re.compile(r"CUIT destino\s*(\d+)")
_BBVA_DEBITADA_IMPORTE_RE = re.compile(r"Importe\s*(ARS|USD)\s*([\d.,]+)")


def parse_bbva_transferencia_debitada(subject: str, body_text: str) -> dict[str, Any] | None:
    fecha_m = _BBVA_DEBITADA_FECHA_RE.search(body_text)
    importe_m = _BBVA_DEBITADA_IMPORTE_RE.search(body_text)
    if not fecha_m or not importe_m:
        return None

    cuit_m = _BBVA_DEBITADA_CUIT_RE.search(body_text)
    cuit = cuit_m.group(1).strip() if cuit_m else ""
    moneda, monto_str = importe_m.groups()
    dd, mm, yyyy = fecha_m.group(1).split("/")

    descripcion = f"Transferencia a CUIT {cuit}" if cuit else "Transferencia inmediata debitada"

    return {
        "monto": _parse_monto_ar(monto_str),
        "moneda": moneda,
        "comercio_raw": "",
        "descripcion": descripcion,
        "tipo": "Gasto",
        "medio_de_pago": "Transferencia BBVA",
        "fecha": f"{yyyy}-{mm}-{dd}",
        "datos_completos": True,
    }


# ---------------------------------------------------------------------------
# BBVA — transferencia inmediata acreditada (INGRESO — mismo template que la
# debitada, pero con "CBU/CUIT origen" en vez de "destino")
# Asuntos: "...AVISO TRANSFERENCIA INMEDIATA ACREDITADA"
# ---------------------------------------------------------------------------

_BBVA_ACREDITADA_FECHA_RE = re.compile(r"Fecha\s*(\d{2}/\d{2}/\d{4})")
_BBVA_ACREDITADA_CUIT_RE = re.compile(r"CUIT origen\s*(\d+)")
_BBVA_ACREDITADA_IMPORTE_RE = re.compile(r"Importe\s*(ARS|USD)\s*([\d.,]+)")


def parse_bbva_transferencia_acreditada(subject: str, body_text: str) -> dict[str, Any] | None:
    fecha_m = _BBVA_ACREDITADA_FECHA_RE.search(body_text)
    importe_m = _BBVA_ACREDITADA_IMPORTE_RE.search(body_text)
    if not fecha_m or not importe_m:
        return None

    cuit_m = _BBVA_ACREDITADA_CUIT_RE.search(body_text)
    cuit = cuit_m.group(1).strip() if cuit_m else ""
    moneda, monto_str = importe_m.groups()
    dd, mm, yyyy = fecha_m.group(1).split("/")

    descripcion = f"Transferencia recibida de CUIT {cuit}" if cuit else "Transferencia inmediata acreditada"

    return {
        "monto": _parse_monto_ar(monto_str),
        "moneda": moneda,
        "comercio_raw": "",
        "descripcion": descripcion,
        "tipo": "Ingreso",
        "medio_de_pago": "Transferencia BBVA",
        "fecha": f"{yyyy}-{mm}-{dd}",
        "datos_completos": True,
    }


# ---------------------------------------------------------------------------
# MercadoPago — pago aprobado
# Asuntos: "Pago aprobado en <comercio>" — el comercio ya viene en el asunto.
# Template: "Pagaste $ X.XXX,XX" + tarjeta "<Banco> Crédito|Débito **** NNNN"
# ---------------------------------------------------------------------------

_MP_SUBJECT_COMERCIO_RE = re.compile(r"pago aprobado en\s+(.+)", re.IGNORECASE)
_MP_MONTO_RE = re.compile(r"Pagaste\s*\$\s*([\d.,]+)")
_MP_TARJETA_RE = re.compile(
    r"([A-Za-zÁÉÍÓÚÑáéíóúñ\s]+?(?:Cr[eé]dito|D[eé]bito))\s*\*{2,4}\s*(\d+)"
)


def parse_mercadopago_pago_aprobado(subject: str, body_text: str) -> dict[str, Any] | None:
    monto_m = _MP_MONTO_RE.search(body_text)
    if not monto_m:
        return None

    comercio_m = _MP_SUBJECT_COMERCIO_RE.search(subject)
    comercio = comercio_m.group(1).strip() if comercio_m else ""

    tarjeta_m = _MP_TARJETA_RE.search(body_text)
    medio_de_pago = tarjeta_m.group(1).strip() if tarjeta_m else "Mercado Pago"

    return {
        "monto": _parse_monto_ar(monto_m.group(1)),
        "moneda": "ARS",
        "comercio_raw": comercio,
        "descripcion": f"Pago a {comercio}" if comercio else "Pago aprobado en Mercado Pago",
        "tipo": "Gasto",
        "medio_de_pago": medio_de_pago,
        "fecha": None,
        "datos_completos": True,
    }


# ---------------------------------------------------------------------------
# MercadoPago — transferencia enviada (retiro a cuenta bancaria propia o de terceros)
# Asuntos: "Tu transferencia fue enviada"
# Template: "Ya enviamos tu transferencia de US$|$ X.XXX" + bloque
# "Nombre y apellido: X Entidad: Y Número de cuenta: Z"
# ---------------------------------------------------------------------------

_MP_TRANSF_MONTO_RE = re.compile(r"transferencia de\s*(US\$|\$)\s*([\d.,]+)", re.IGNORECASE)
_MP_TRANSF_NOMBRE_RE = re.compile(r"Nombre y apellido:\s*(.+?)\s*Entidad:")
_MP_TRANSF_ENTIDAD_RE = re.compile(r"Entidad:\s*(.+?)\s*N[uú]mero de cuenta:")


def parse_mercadopago_transferencia_enviada(subject: str, body_text: str) -> dict[str, Any] | None:
    monto_m = _MP_TRANSF_MONTO_RE.search(body_text)
    if not monto_m:
        return None

    simbolo, monto_str = monto_m.groups()
    moneda = "USD" if "US" in simbolo else "ARS"

    nombre_m = _MP_TRANSF_NOMBRE_RE.search(body_text)
    entidad_m = _MP_TRANSF_ENTIDAD_RE.search(body_text)
    beneficiario = nombre_m.group(1).strip() if nombre_m else ""
    entidad = entidad_m.group(1).strip() if entidad_m else ""

    descripcion = f"Transferencia a {beneficiario}" if beneficiario else "Transferencia enviada"
    medio_de_pago = f"Transferencia Mercado Pago a {entidad}" if entidad else "Transferencia Mercado Pago"

    return {
        "monto": _parse_monto_ar(monto_str),
        "moneda": moneda,
        "comercio_raw": beneficiario,
        "descripcion": descripcion,
        "tipo": "Gasto",
        "medio_de_pago": medio_de_pago,
        "fecha": None,
        "datos_completos": True,
    }


# ---------------------------------------------------------------------------
# Dispatch table: (sender_substring, subject_substring) -> parser
# Se completa a medida que sumamos templates.
# ---------------------------------------------------------------------------

_PARSERS: list[tuple[str, str, Any]] = [
    ("bbva", "compra", parse_bbva_compra),
    ("bbva", "nueva compra", parse_bbva_compra),
    ("bbva", "realizaste una transferencia", parse_bbva_transferencia_enviada),
    ("bbva", "transferencia inmediata debitada", parse_bbva_transferencia_debitada),
    ("bbva", "transferencia inmediata acreditada", parse_bbva_transferencia_acreditada),
    ("mercadopago", "pago aprobado", parse_mercadopago_pago_aprobado),
    ("mercadopago", "tu transferencia fue enviada", parse_mercadopago_transferencia_enviada),
]


def try_parse_with_regex(sender: str, subject: str, body_text: str) -> dict[str, Any] | None:
    """Try a deterministic parser for known sender+subject templates. Returns None if no match."""
    sender_l = sender.lower()
    subject_l = subject.lower()
    for sender_sub, subject_sub, parser in _PARSERS:
        if sender_sub in sender_l and subject_sub in subject_l:
            result = parser(subject, body_text)
            if result is not None:
                return result
    return None
