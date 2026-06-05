"""Actualiza la password de Ignacio en Neon a 'miPassword123'."""
import asyncio
import sys
sys.path.insert(0, '.')
from app.db.session import get_async_engine
from app.core.security import hash_password, verify_password
from sqlalchemy import text

NEW_PASSWORD = "miPassword123"

async def fix():
    engine = get_async_engine()
    new_hash = hash_password(NEW_PASSWORD)
    async with engine.begin() as conn:
        await conn.execute(
            text('UPDATE "MaestroUsuarios" SET "PasswordHash" = :h WHERE id = 11'),
            {"h": new_hash}
        )
    print(f"Password actualizada. Hash: {new_hash[:30]}...")
    print("Verificacion:", verify_password(NEW_PASSWORD, new_hash))

asyncio.run(fix())
