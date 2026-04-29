"""
Bank email filters — detect which emails are expense notifications.

Used by the Gmail poller to pre-filter emails before GPT extraction.
Based on the patterns currently used by n8n triggers.
"""
from __future__ import annotations

# Each filter: if sender contains X AND subject contains Y → it's a bank notification
BANK_FILTERS = [
    # Santander Argentina
    {"sender": "santander", "subjects": ["Pagaste", "Compraste", "Aviso de transferencia"]},
    # BBVA Argentina
    {"sender": "bbva", "subjects": ["Nueva compra", "Compra aprobada", "Realizaste una transferencia"]},
    # Banco Macro
    {"sender": "macro", "subjects": ["Aviso de compra"]},
    # MercadoPago
    {"sender": "mercadopago", "subjects": ["Pago aprobado", "Tu transferencia fue enviada", "Pagaste"]},
    # Banco Galicia
    {"sender": "galicia", "subjects": ["compra", "Aviso de débito"]},
    # Naranja X
    {"sender": "naranjax", "subjects": ["compra", "pago"]},
    {"sender": "naranja", "subjects": ["Resumen", "compra"]},
    # Brubank
    {"sender": "brubank", "subjects": ["compra", "transferencia"]},
    # Ualá
    {"sender": "uala", "subjects": ["compra", "pago"]},
]


def matches_bank_filter(sender: str, subject: str) -> bool:
    """Check if an email matches any known bank expense notification pattern."""
    sender_lower = sender.lower()
    subject_lower = subject.lower()
    for f in BANK_FILTERS:
        if f["sender"] in sender_lower:
            if any(s.lower() in subject_lower for s in f["subjects"]):
                return True
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
