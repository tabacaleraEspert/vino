import asyncio, asyncpg

async def main():
    conn = await asyncpg.connect("postgresql://neondb_owner:npg_KwWqRJ8oA9QX@ep-silent-dream-apxn8h3v.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require")
    # Set cursor to COPETIN email (just before AVISO TRANSFERENCIA INMEDIATA DEBITADA)
    # so next poll picks up the transfer email again with the new extractor
    await conn.execute('UPDATE "MaestroUsuarios" SET "GmailLastMessageId" = $1 WHERE id = 11', '19ea706a188c0646')
    row = await conn.fetchrow('SELECT "GmailLastMessageId" FROM "MaestroUsuarios" WHERE id = 11')
    print(f"Cursor ahora: {row['GmailLastMessageId']}")
    await conn.close()

asyncio.run(main())
