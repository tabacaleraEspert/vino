"""Seed default categories and subcategories for new users."""
from __future__ import annotations

import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.categoria import Categoria
from app.models.subcategoria import SubCategoria

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = [
    {
        "nombre": "Alimentos",
        "icon": "🍕",
        "color": "#14b8a6",
        "subcategorias": [
            "Supermercado", "Restaurant", "Delivery", "Kiosco / Snacks",
            "Verdulería", "Café / Merienda", "Otros - Alimentos",
        ],
    },
    {
        "nombre": "Transporte",
        "icon": "🚗",
        "color": "#f97316",
        "subcategorias": [
            "Combustible", "Estacionamiento", "Peajes",
            "Taxi / Uber / Cabify", "Transporte público", "Mantenimiento auto",
            "Otros - Transporte",
        ],
    },
    {
        "nombre": "Vivienda",
        "icon": "🏠",
        "color": "#ec4899",
        "subcategorias": [
            "Alquiler / Hipoteca", "Expensas", "Servicios (luz, gas, agua)",
            "Internet / Cable", "Reparaciones", "Muebles / Deco",
            "Otros - Vivienda",
        ],
    },
    {
        "nombre": "Entretenimiento / Social",
        "icon": "🎬",
        "color": "#eab308",
        "subcategorias": [
            "Salidas / Bares", "Cine / Teatro", "Streaming / Suscripciones",
            "Deportes / Gym", "Viajes / Vacaciones", "Hobbies",
            "Otros - Entretenimiento",
        ],
    },
    {
        "nombre": "Educación y Salud",
        "icon": "⚕️",
        "color": "#06b6d4",
        "subcategorias": [
            "Farmacia", "Consultas médicas", "Prepaga / Obra social",
            "Cursos / Capacitación", "Libros / Material",
            "Otros - Educación y Salud",
        ],
    },
    {
        "nombre": "Ropa",
        "icon": "👕",
        "color": "#57534e",
        "subcategorias": [
            "Ropa casual", "Calzado", "Accesorios", "Ropa deportiva",
            "Otros - Ropa",
        ],
    },
    {
        "nombre": "Otros",
        "icon": "📁",
        "color": "#6b7280",
        "subcategorias": [
            "Gastos no categorizados", "Regalos", "Mascotas",
            "Impuestos / Trámites", "Fintech / Transferencias",
            "Otros - Varios",
        ],
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
