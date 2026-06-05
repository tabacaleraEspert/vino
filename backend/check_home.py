import asyncio
from dotenv import load_dotenv
load_dotenv()
from app.db.session import get_async_engine
from sqlalchemy import text

async def run():
    engine = get_async_engine()
    async with engine.connect() as conn:

        # Presupuestos
        r = await conn.execute(text(
            "SELECT COUNT(*), SUM(Monto) FROM Presupuestos WHERE Id_usuario = 11"
        ))
        row = r.fetchone()
        print(f'Presupuestos: {row[0]} registros, total ${row[1]}')

        # Top gastos por categoria
        r2 = await conn.execute(text("""
            SELECT TOP 5 c.Nombre, COUNT(*) as cant, SUM(m.Monto) as total
            FROM Movimientos m
            LEFT JOIN Categoria c ON m.Id_Categoria = c.Id
            WHERE m.Id_usuario = 11
              AND m.Fecha >= '2026-05-01' AND m.Fecha <= '2026-05-31'
              AND m.TipoMovimiento = 'Gasto'
            GROUP BY c.Nombre
            ORDER BY total DESC
        """))
        rows = r2.fetchall()
        print('\nTop categorias mayo:')
        for row in rows:
            print(f'  {row[0]}: {row[1]} movs, ${row[2]:,.0f}')

asyncio.run(run())
