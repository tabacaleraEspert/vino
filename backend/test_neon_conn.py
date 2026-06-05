import asyncio
import sys
sys.path.insert(0, '.')
from app.db.session import get_async_engine
from sqlalchemy import text

async def test():
    engine = get_async_engine()
    async with engine.begin() as conn:
        result = await conn.execute(text('SELECT COUNT(*) FROM "MaestroUsuarios"'))
        count = result.scalar()
        print("Conexion Neon OK. Usuarios:", count)
        result2 = await conn.execute(text('SELECT COUNT(*) FROM movimientos'))
        print("Movimientos:", result2.scalar())

asyncio.run(test())
