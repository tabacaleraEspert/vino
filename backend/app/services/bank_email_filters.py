"""
Bank email filters — detect which emails are expense or income notifications.

Used by the Gmail poller to pre-filter emails before GPT extraction.
Based on the patterns currently used by n8n triggers.
"""
from __future__ import annotations

# Each filter: if sender contains X AND subject contains Y → it's a bank notification
# tipo: "Gasto" (default) or "Ingreso" — helps hint the GPT extractor
BANK_FILTERS = [
    # --- GASTOS ---
    # Santander Argentina (n8n: Gmail DV, Gmail MM)
    {"sender": "santander", "subjects": ["Pagaste", "Compraste", "Aviso de transferencia"], "tipo": "Gasto"},
    # BBVA Argentina (n8n: Gmail IM, Gmail Loli)
    # Note: BBVA uses two subject formats — old ("Compra aprobada") and new ("Mensajes y Avisos...")
    {"sender": "bbva", "subjects": [
        "Nueva compra", "Compra aprobada", "Realizaste una transferencia",
        "AVISO TRANSFERENCIA INMEDIATA DEBITADA", "AVISO DE COMPRA",
    ], "tipo": "Gasto"},
    # Banco Macro (n8n: Gmail MM)
    {"sender": "macro", "subjects": ["Aviso de compra"], "tipo": "Gasto"},
    # MercadoPago (n8n: Gmail IM, Gmail Loli)
    {"sender": "mercadopago", "subjects": ["Pago aprobado en", "Pago aprobado", "Tu transferencia fue enviada", "Pagaste"], "tipo": "Gasto"},
    # Banco Galicia
    {"sender": "galicia", "subjects": ["compra", "Aviso de débito"], "tipo": "Gasto"},
    # Naranja X
    {"sender": "naranjax", "subjects": ["compra", "pago"], "tipo": "Gasto"},
    {"sender": "naranja", "subjects": ["compra"], "tipo": "Gasto"},
    # Brubank
    {"sender": "brubank", "subjects": ["compra"], "tipo": "Gasto"},
    # Uala
    {"sender": "uala", "subjects": ["compra", "pago"], "tipo": "Gasto"},

    # --- INGRESOS ---
    # Santander
    {"sender": "santander", "subjects": ["Transferencia recibida", "Te transfirieron", "Recibiste una transferencia"], "tipo": "Ingreso"},
    # BBVA
    {"sender": "bbva", "subjects": [
        "Recibiste una transferencia", "Te transfirieron",
        "AVISO TRANSFERENCIA INMEDIATA ACREDITADA",
    ], "tipo": "Ingreso"},
    # Banco Macro
    {"sender": "macro", "subjects": ["Transferencia recibida", "Te transfirieron"], "tipo": "Ingreso"},
    # MercadoPago
    {"sender": "mercadopago", "subjects": ["Te enviaron dinero", "Recibiste un pago", "Te transfirieron dinero", "Cobro acreditado"], "tipo": "Ingreso"},
    # Banco Galicia
    {"sender": "galicia", "subjects": ["Transferencia recibida", "Te transfirieron"], "tipo": "Ingreso"},
    # Brubank
    {"sender": "brubank", "subjects": ["Recibiste una transferencia", "Te transfirieron"], "tipo": "Ingreso"},
    # Uala
    {"sender": "uala", "subjects": ["Recibiste dinero", "Te transfirieron"], "tipo": "Ingreso"},
]


def matches_bank_filter(sender: str, subject: str) -> bool | tuple[bool, str]:
    """Check if an email matches any known bank notification pattern.
    Returns (True, tipo) if matched, False otherwise."""
    sender_lower = sender.lower()
    subject_lower = subject.lower()
    for f in BANK_FILTERS:
        if f["sender"] in sender_lower:
            if any(s.lower() in subject_lower for s in f["subjects"]):
                return True, f.get("tipo", "Gasto")
    return False


def build_gmail_query(days_back: int = 1) -> str:
    """
    Build a Gmail API search query that matches bank expense emails.

    Returns a query like:
    from:(santander OR bbva OR mercadopago) newer_than:1d
    """
    senders = sorted({f["sender"] for f in BANK_FILTERS})
    sender_clause = " OR ".join(senders)
    return f"from:({sender_clause}) newer_than:{days_back}d"
