import asyncio
from dotenv import load_dotenv
load_dotenv()
from app.db.session import get_async_engine
from sqlalchemy import text

async def run():
    engine = get_async_engine()
    async with engine.begin() as conn:
        # Find the table schema
        result = await conn.execute(text(
            "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'MaestroUsuarios'"
        ))
        rows = result.fetchall()
        print('Tabla encontrada en:', rows)

        if rows:
            schema = rows[0][0]
            try:
                await conn.execute(text(
                    f"ALTER TABLE [{schema}].[MaestroUsuarios] ADD Apodo NVARCHAR(50) NULL"
                ))
                print('OK: columna Apodo agregada')
            except Exception as e:
                if 'Column names in each table must be unique' in str(e):
                    print('OK: columna Apodo ya existe')
                else:
                    print(f'ERROR: {e}')

asyncio.run(run())
