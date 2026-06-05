import asyncio
import sys
sys.path.insert(0, '.')
from app.db.session import get_async_engine
from sqlalchemy import text

async def test():
    engine = get_async_engine()
    async with engine.begin() as conn:
        # Check what's in the user table
        result = await conn.execute(text('SELECT id, "Nombre", "PasswordHash", gmail FROM "MaestroUsuarios"'))
        rows = result.fetchall()
        for r in rows:
            print(f"id={r[0]}, Nombre={r[1]!r}, PasswordHash={r[2][:30] if r[2] else None}..., gmail={r[3]}")

asyncio.run(test())
