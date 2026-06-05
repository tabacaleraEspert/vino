"""
Dev helper: set a password for a user so they can log in locally with email+password.
Usage:  python set_local_password.py
"""
import asyncio
from dotenv import load_dotenv
load_dotenv()

from app.db.session import get_async_engine
from app.core.security import hash_password
from sqlalchemy import text

TARGET_GMAIL = "ignamedico@gmail.com"
NEW_PASSWORD = "fina2026"   # temporary local password


async def run():
    engine = get_async_engine()
    async with engine.begin() as conn:
        # Find user
        r = await conn.execute(
            text("SELECT id, Nombre, Apellido, gmail, PasswordHash FROM dbo.MaestroUsuarios WHERE gmail = :g"),
            {"g": TARGET_GMAIL},
        )
        user = r.fetchone()
        if not user:
            print(f"ERROR: no user found with gmail={TARGET_GMAIL}")
            return

        uid, nombre, apellido, gmail, current_hash = user
        print(f"Found user: id={uid}, nombre={nombre}, gmail={gmail}")
        print(f"Current PasswordHash: {'(set)' if current_hash else '(empty)'}")

        hashed = hash_password(NEW_PASSWORD)
        await conn.execute(
            text("UPDATE dbo.MaestroUsuarios SET PasswordHash = :h WHERE id = :uid"),
            {"h": hashed, "uid": uid},
        )
        print(f"\nPassword updated successfully!")
        print(f"You can now log in with:")
        print(f"  Email:    {TARGET_GMAIL}")
        print(f"  Password: {NEW_PASSWORD}")


asyncio.run(run())
