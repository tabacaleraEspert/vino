#!/usr/bin/env python3
"""
Script para setear/actualizar el password de un usuario en Azure SQL.
Uso: python -m scripts.set_password <nombre_usuario> <password>
Ejemplo: python -m scripts.set_password Davor miPassword123

Requiere: SQL_SERVER, SQL_DB, SQL_USER, SQL_PASSWORD en .env
"""
import sys
from pathlib import Path

# Asegurar que app está en el path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.security import hash_password
from app.db.connection import get_connection


def main():
    if len(sys.argv) < 3:
        print("Uso: python -m scripts.set_password <nombre_usuario> <password>")
        print("Ejemplo: python -m scripts.set_password Davor miPassword123")
        sys.exit(1)

    nombre = sys.argv[1].strip()
    password = sys.argv[2]
    if not nombre or not password:
        print("Error: nombre y password no pueden estar vacíos")
        sys.exit(1)

    hashed = hash_password(password)
    table = settings.SQL_USUARIO_TABLE

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE [{table}] SET PasswordHash = ?, UpdatedAt = GETUTCDATE() WHERE Nombre = ?",
                (hashed, nombre),
            )
            if cursor.rowcount == 0:
                print(f"Error: No se encontró usuario con Nombre='{nombre}'")
                sys.exit(1)
            conn.commit()
        print(f"OK: Password actualizado para usuario '{nombre}'")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
