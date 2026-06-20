import asyncio, asyncpg

async def main():
    conn = await asyncpg.connect("postgresql://neondb_owner:npg_KwWqRJ8oA9QX@ep-silent-dream-apxn8h3v.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require")
    rows = await conn.fetch("""
        SELECT
            u.id,
            u."Nombre",
            u.gmail,
            u."WppEntero",
            COUNT(CASE WHEN DATE(m."Timestamp") = CURRENT_DATE THEN 1 END) as movs_hoy,
            COUNT(CASE WHEN DATE(m."Timestamp") >= CURRENT_DATE - 7 THEN 1 END) as movs_7dias,
            MAX(m."Timestamp") as ultimo_mov
        FROM "MaestroUsuarios" u
        LEFT JOIN movimientos m ON m."Id_usuario" = u.id
        GROUP BY u.id, u."Nombre", u.gmail, u."WppEntero"
        ORDER BY ultimo_mov DESC NULLS LAST
    """)
    for r in rows:
        wpp = "si" if r["WppEntero"] else "no"
        ultimo = str(r["ultimo_mov"])[:10] if r["ultimo_mov"] else "nunca"
        gmail = r["gmail"] or ""
        nombre = str(r["Nombre"] or "")
        print(f"id={r['id']:3} | {nombre:<12} | wpp={wpp} | hoy={r['movs_hoy']} | 7dias={r['movs_7dias']} | ultimo={ultimo} | {gmail}")
    await conn.close()

asyncio.run(main())
