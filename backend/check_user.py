import asyncio
from dotenv import load_dotenv
load_dotenv()
from app.db.session import get_async_engine
from sqlalchemy import text

async def run():
    engine = get_async_engine()
    async with engine.connect() as conn:
        # Find Ignacio's user
        r = await conn.execute(text(
            "SELECT id, Nombre, Apellido, gmail FROM dbo.MaestroUsuarios WHERE gmail = 'ignamedico@gmail.com' OR Nombre LIKE '%gnacio%'"
        ))
        users = r.fetchall()
        print('Usuarios encontrados:', users)

        if users:
            user_id = users[0][0]
            print(f'\nBuscando movimientos para id_usuario = {user_id}...')

            # Count movimientos
            r2 = await conn.execute(text(
                f"SELECT COUNT(*) as total, MIN(Fecha) as primer_mov, MAX(Fecha) as ultimo_mov FROM dbo.Movimientos WHERE Id_usuario = {user_id}"
            ))
            stats = r2.fetchone()
            print(f'Total movimientos: {stats[0]}')
            print(f'Primer movimiento: {stats[1]}')
            print(f'Ultimo movimiento: {stats[2]}')

            # Sample last 5
            r3 = await conn.execute(text(
                f"SELECT TOP 5 Fecha, Monto, Descripcion, MedioCarga FROM dbo.Movimientos WHERE Id_usuario = {user_id} ORDER BY Fecha DESC"
            ))
            rows = r3.fetchall()
            print('\nUltimos 5 movimientos:')
            for row in rows:
                print(f'  {row[0]} | ${row[1]} | {row[2]} | {row[3]}')

asyncio.run(run())
