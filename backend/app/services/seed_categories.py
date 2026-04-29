"""Seed default categories and subcategories for new users."""
from __future__ import annotations

import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.categoria import Categoria
from app.models.subcategoria import SubCategoria

logger = logging.getLogger(__name__)

# Buckets for 50/30/20 rule
BUCKET_NECESIDADES = "necesidades"    # 50%
BUCKET_ESTILO_VIDA = "estilo_vida"    # 30%
BUCKET_FUTURO = "futuro"              # 20%

DEFAULT_CATEGORIES = [
    # ── Necesidades (50%) ──
    {
        "nombre": "Vivienda",
        "icon": "🏠",
        "color": "#ec4899",
        "bucket": BUCKET_NECESIDADES,
        "subcategorias": ["Alquiler", "Expensas", "Hipoteca", "Mantenimiento"],
    },
    {
        "nombre": "Comida",
        "icon": "🍴",
        "color": "#14b8a6",
        "bucket": BUCKET_NECESIDADES,
        "subcategorias": ["Súper", "Almacén", "Verdulería", "Carnicería", "Delivery"],
    },
    {
        "nombre": "Transporte",
        "icon": "🚗",
        "color": "#f97316",
        "bucket": BUCKET_NECESIDADES,
        "subcategorias": ["Nafta", "SUBE", "Uber", "Estacionamiento", "Peajes"],
    },
    {
        "nombre": "Servicios",
        "icon": "💡",
        "color": "#eab308",
        "bucket": BUCKET_NECESIDADES,
        "subcategorias": ["Luz", "Gas", "Agua", "Internet", "Celular"],
    },
    {
        "nombre": "Salud",
        "icon": "💊",
        "color": "#06b6d4",
        "bucket": BUCKET_NECESIDADES,
        "subcategorias": ["Prepaga", "Farmacia", "Consultas", "Gimnasio"],
    },
    {
        "nombre": "Educación",
        "icon": "🎓",
        "color": "#8b5cf6",
        "bucket": BUCKET_NECESIDADES,
        "subcategorias": ["Cuotas", "Cursos", "Libros"],
    },
    # ── Estilo de vida (30%) ──
    {
        "nombre": "Salidas",
        "icon": "🍻",
        "color": "#ef4444",
        "bucket": BUCKET_ESTILO_VIDA,
        "subcategorias": ["Restaurantes", "Bar", "Café", "Eventos"],
    },
    {
        "nombre": "Ocio",
        "icon": "🎬",
        "color": "#d946ef",
        "bucket": BUCKET_ESTILO_VIDA,
        "subcategorias": ["Cine", "Streaming", "Viajes", "Hobbies"],
    },
    {
        "nombre": "Compras",
        "icon": "👕",
        "color": "#57534e",
        "bucket": BUCKET_ESTILO_VIDA,
        "subcategorias": ["Ropa", "Calzado", "Hogar", "Tecnología"],
    },
    # ── Futuro (20%) ──
    {
        "nombre": "Ahorro",
        "icon": "💰",
        "color": "#10b981",
        "bucket": BUCKET_FUTURO,
        "subcategorias": ["Caja", "Plazo fijo", "Emergencia", "Metas"],
    },
    {
        "nombre": "Inversión",
        "icon": "📈",
        "color": "#3b82f6",
        "bucket": BUCKET_FUTURO,
        "subcategorias": ["Acciones", "FCI", "Cripto", "Dólar"],
    },
]


async def seed_default_categories(db: AsyncSession, id_usuario: int) -> int:
    """Create default categories + subcategories for a new user. Returns count created."""
    created = 0
    for cat_data in DEFAULT_CATEGORIES:
        cat = Categoria(
            Id_usuario=id_usuario,
            Nombre=cat_data["nombre"],
            Icon=cat_data["icon"],
            Color=cat_data["color"],
            Bucket=cat_data.get("bucket"),
        )
        db.add(cat)
        await db.flush()  # get cat.Id

        for sub_name in cat_data["subcategorias"]:
            sub = SubCategoria(
                Id_usuario=id_usuario,
                Id_Categoria=cat.Id,
                Nombre_SubCategoria=sub_name,
            )
            db.add(sub)
            created += 1

        created += 1

    # Seed default wallets
    from app.models.billetera import Billetera
    default_wallets = [
        {"nombre": "Cuenta Pesos", "moneda": "ARS", "icono": "🇦🇷", "color": "#14b8a6", "es_default": True},
        {"nombre": "Cuenta Dólares", "moneda": "USD", "icono": "🇺🇸", "color": "#3b82f6", "es_default": False},
    ]
    for w in default_wallets:
        wallet = Billetera(
            Id_usuario=id_usuario,
            Nombre=w["nombre"],
            Moneda=w["moneda"],
            Icono=w["icono"],
            Color=w["color"],
            EsDefault=w["es_default"],
        )
        db.add(wallet)
        created += 1

    await db.flush()
    logger.info("Seeded %d categories+subcategories+wallets for user %d", created, id_usuario)
    return created
