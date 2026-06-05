import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

NEON_URL = "postgresql+asyncpg://neondb_owner:npg_KwWqRJ8oA9QX@ep-silent-dream-apxn8h3v.c-7.us-east-1.aws.neon.tech/neondb?ssl=require"

async def check():
    engine = create_async_engine(NEON_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        for table in ["MaestroUsuarios", "Categoria", "SubCategoria", "ReglaComercio", "Presupuestos", "movimientos"]:
            r = await s.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
            print(f"{table}: {r.scalar()} rows")
    await engine.dispose()

asyncio.run(check())
