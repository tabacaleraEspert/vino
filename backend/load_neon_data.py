"""
Carga todos los datos del backup (ahorros_backup_ignacio.json) a Neon PostgreSQL.
Ejecutar: python load_neon_data.py
"""
import asyncio
import json
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

NEON_URL = "postgresql+asyncpg://neondb_owner:npg_KwWqRJ8oA9QX@ep-silent-dream-apxn8h3v.c-7.us-east-1.aws.neon.tech/neondb?ssl=require"
BACKUP_FILE = "C:/Users/Familia/OneDrive/Escritorio/ahorros_backup_ignacio.json"


def to_int(v):
    return int(v) if v is not None else None


def to_dt(v):
    if v is None:
        return None
    if isinstance(v, (datetime, date)):
        return v
    return datetime.fromisoformat(str(v))


def to_date(v):
    if v is None:
        return None
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def to_dec(v):
    return Decimal(str(v)) if v is not None else None


def to_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() == "true"
    return bool(v) if v is not None else False


async def main():
    with open(BACKUP_FILE, encoding="utf-8") as f:
        data = json.load(f)

    engine = create_async_engine(NEON_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        async with session.begin():

            # ----------------------------------------------------------------
            # 1. Usuario (skip if already exists)
            # ----------------------------------------------------------------
            # "usuario" is a list with one element
            u = data["usuario"][0] if isinstance(data["usuario"], list) else data["usuario"]
            await session.execute(text("""
                INSERT INTO "MaestroUsuarios"
                    (id, "Nombre", "Apellido", "WppEntero", "Whatsapp", gmail,
                     "ID_Sheets", "PasswordHash", "OnboardingCompletado",
                     "OnboardingCompletadoAt", "OnboardingStep",
                     "GmailRefreshToken", "GmailConnectedAt", "GmailLastPolledAt",
                     "GmailLastMessageId", "WppOtpCode", "WppOtpExpiresAt",
                     "WppOtpPhone", "CreatedAt", "UpdatedAt")
                VALUES
                    (:id, :nombre, :apellido, :wpp_entero, :whatsapp, :gmail,
                     :id_sheets, :pw_hash, :onboarding,
                     :onboarding_at, :onboarding_step,
                     :grt, :gca, :glpa,
                     :glmi, :otp_code, :otp_exp,
                     :otp_phone, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": to_int(u.get("id")),
                "nombre": u.get("Nombre"),
                "apellido": u.get("Apellido"),
                "wpp_entero": u.get("WppEntero"),
                "whatsapp": u.get("Whatsapp"),
                "gmail": u.get("gmail"),
                "id_sheets": u.get("ID_Sheets"),
                "pw_hash": u.get("PasswordHash"),
                "onboarding": to_bool(u.get("OnboardingCompletado", False)),
                "onboarding_at": to_dt(u.get("OnboardingCompletadoAt")),
                "onboarding_step": to_int(u.get("OnboardingStep", 0)),
                "grt": u.get("GmailRefreshToken"),
                "gca": to_dt(u.get("GmailConnectedAt")),
                "glpa": to_dt(u.get("GmailLastPolledAt")),
                "glmi": u.get("GmailLastMessageId"),
                "otp_code": u.get("WppOtpCode"),
                "otp_exp": to_dt(u.get("WppOtpExpiresAt")),
                "otp_phone": u.get("WppOtpPhone"),
                "created_at": to_dt(u.get("CreatedAt")),
                "updated_at": to_dt(u.get("UpdatedAt")),
            })
            print(f"Usuario: insertado o ya existia (id={u.get('id')})")

            # ----------------------------------------------------------------
            # 2. Categorias
            # ----------------------------------------------------------------
            ok = 0
            for c in data["categorias"]:
                await session.execute(text("""
                    INSERT INTO "Categoria"
                        ("Id", "Id_usuario", "Nombre", "Icon", "Color", "Bucket", "Tipo", "Timestamp")
                    VALUES
                        (:id, :uid, :nombre, :icon, :color, :bucket, :tipo, :ts)
                    ON CONFLICT ("Id") DO NOTHING
                """), {
                    "id": to_int(c["Id"]),
                    "uid": to_int(c["Id_usuario"]),
                    "nombre": c.get("Nombre"),
                    "icon": c.get("Icon"),
                    "color": c.get("Color"),
                    "bucket": c.get("Bucket"),
                    "tipo": c.get("Tipo", "Gasto"),
                    "ts": to_dt(c.get("Timestamp")),
                })
                ok += 1
            print(f"Categorias: {ok} insertadas")

            # ----------------------------------------------------------------
            # 3. SubCategorias
            # ----------------------------------------------------------------
            ok = 0
            for s in data["subcategorias"]:
                await session.execute(text("""
                    INSERT INTO "SubCategoria"
                        ("Id", "Id_usuario", "Id_Categoria", "Nombre_SubCategoria", "Timestamp")
                    VALUES
                        (:id, :uid, :id_cat, :nombre, :ts)
                    ON CONFLICT ("Id") DO NOTHING
                """), {
                    "id": to_int(s["Id"]),
                    "uid": to_int(s["Id_usuario"]),
                    "id_cat": to_int(s["Id_Categoria"]),
                    "nombre": s.get("Nombre_SubCategoria"),
                    "ts": to_dt(s.get("Timestamp")),
                })
                ok += 1
            print(f"SubCategorias: {ok} insertadas")

            # ----------------------------------------------------------------
            # 4. ReglaComercio
            # ----------------------------------------------------------------
            ok = 0
            for r in data["reglas"]:
                await session.execute(text("""
                    INSERT INTO "ReglaComercio"
                        ("Id", "Id_usuario", "Patron", "PatronNorm", "EjemploRazonSocial",
                         "Id_Categoria", "Id_SubCategoria", "Prioridad", "Activa",
                         "Confianza", "TipoMovimiento", "CreadoEn", "ActualizadoEn")
                    VALUES
                        (:id, :uid, :patron, :patron_norm, :ejemplo,
                         :id_cat, :id_subcat, :prioridad, :activa,
                         :confianza, :tipo, :creado, :actualizado)
                    ON CONFLICT ("Id") DO NOTHING
                """), {
                    "id": to_int(r["Id"]),
                    "uid": to_int(r["Id_usuario"]),
                    "patron": r.get("Patron"),
                    "patron_norm": r.get("PatronNorm"),
                    "ejemplo": r.get("EjemploRazonSocial"),
                    "id_cat": to_int(r["Id_Categoria"]),
                    "id_subcat": to_int(r["Id_SubCategoria"]),
                    "prioridad": to_int(r.get("Prioridad", 100)),
                    "activa": to_bool(r.get("Activa", True)),
                    "confianza": r.get("Confianza", "AUTO"),
                    "tipo": r.get("TipoMovimiento", "Gasto"),
                    "creado": to_dt(r.get("CreadoEn")),
                    "actualizado": to_dt(r.get("ActualizadoEn")),
                })
                ok += 1
            print(f"ReglaComercio: {ok} insertadas")

            # ----------------------------------------------------------------
            # 5. Presupuestos
            # ----------------------------------------------------------------
            ok = 0
            for p in data["presupuestos"]:
                await session.execute(text("""
                    INSERT INTO "Presupuestos"
                        ("Id", "Id_usuario", "PeriodoMes", "Id_Categoria",
                         "Id_SubCategoria", "Monto", "Timestamp")
                    VALUES
                        (:id, :uid, :periodo, :id_cat, :id_subcat, :monto, :ts)
                    ON CONFLICT ("Id") DO NOTHING
                """), {
                    "id": to_int(p["Id"]),
                    "uid": to_int(p["Id_usuario"]),
                    "periodo": to_date(p["PeriodoMes"]),
                    "id_cat": to_int(p.get("Id_Categoria")),
                    "id_subcat": to_int(p.get("Id_SubCategoria")),
                    "monto": to_dec(p["Monto"]),
                    "ts": to_dt(p.get("Timestamp")),
                })
                ok += 1
            print(f"Presupuestos: {ok} insertados")

            # ----------------------------------------------------------------
            # 6. Movimientos
            # ----------------------------------------------------------------
            ok = 0
            for m in data["movimientos"]:
                await session.execute(text("""
                    INSERT INTO movimientos
                        ("Id", "Id_usuario", "Fecha", "Timestamp", "MedioCarga",
                         "TipoMovimiento", "Moneda", "Monto", "Id_Credito_Debito",
                         "Id_Medio_Pago_Final", "Descripcion", "Id_Categoria",
                         "Id_SubCategoria", "Origen", "Origen_Id", "ComercioRaw",
                         "ComercioNorm", "ComercioId", "ReglaComercioId",
                         "CategoriaManual", "CuotaActual", "CuotaTotal",
                         "MontoTotalCompra", "Id_Billetera", "EsSplit",
                         "SplitTotal", "SplitParticipantes")
                    VALUES
                        (:id, :uid, :fecha, :ts, :medio,
                         :tipo, :moneda, :monto, :id_cd,
                         :id_mpf, :desc, :id_cat,
                         :id_subcat, :origen, :origen_id, :comercio_raw,
                         :comercio_norm, :comercio_id, :regla_id,
                         :cat_manual, :cuota_actual, :cuota_total,
                         :monto_total, :billetera, :es_split,
                         :split_total, :split_part)
                    ON CONFLICT ("Id") DO NOTHING
                """), {
                    "id": to_int(m["Id"]),
                    "uid": to_int(m["Id_usuario"]),
                    "fecha": to_date(m["Fecha"]),
                    "ts": to_dt(m.get("Timestamp")),
                    "medio": m.get("MedioCarga", "Manual"),
                    "tipo": m.get("TipoMovimiento", "Gasto"),
                    "moneda": m.get("Moneda", "ARS"),
                    "monto": to_dec(m["Monto"]),
                    "id_cd": to_int(m.get("Id_Credito_Debito")),
                    "id_mpf": to_int(m.get("Id_Medio_Pago_Final")),
                    "desc": m.get("Descripcion"),
                    "id_cat": to_int(m.get("Id_Categoria")),
                    "id_subcat": to_int(m.get("Id_SubCategoria")),
                    "origen": m.get("Origen"),
                    "origen_id": m.get("Origen_Id"),
                    "comercio_raw": m.get("ComercioRaw"),
                    "comercio_norm": m.get("ComercioNorm"),
                    "comercio_id": str(m["ComercioId"]) if m.get("ComercioId") is not None else None,
                    "regla_id": to_int(m.get("ReglaComercioId")),
                    "cat_manual": to_bool(m.get("CategoriaManual", False)),
                    "cuota_actual": to_int(m.get("CuotaActual")),
                    "cuota_total": to_int(m.get("CuotaTotal")),
                    "monto_total": to_dec(m.get("MontoTotalCompra")),
                    "billetera": to_int(m.get("Id_Billetera")),
                    "es_split": to_bool(m.get("EsSplit", False)),
                    "split_total": to_dec(m.get("SplitTotal")),
                    "split_part": to_int(m.get("SplitParticipantes")),
                })
                ok += 1
            print(f"Movimientos: {ok} insertados")

        # --------------------------------------------------------------------
        # Reset PostgreSQL sequences so autoincrement doesn't collide
        # --------------------------------------------------------------------
        print("\nReseteando secuencias...")
        async with session.begin():
            await session.execute(text("""
                SELECT setval(pg_get_serial_sequence('"Categoria"', 'Id'),
                    GREATEST((SELECT MAX("Id") FROM "Categoria"), 1))
            """))
            await session.execute(text("""
                SELECT setval(pg_get_serial_sequence('"SubCategoria"', 'Id'),
                    GREATEST((SELECT MAX("Id") FROM "SubCategoria"), 1))
            """))
            await session.execute(text("""
                SELECT setval(pg_get_serial_sequence('"ReglaComercio"', 'Id'),
                    GREATEST((SELECT MAX("Id") FROM "ReglaComercio"), 1))
            """))
            await session.execute(text("""
                SELECT setval(pg_get_serial_sequence('"Presupuestos"', 'Id'),
                    GREATEST((SELECT MAX("Id") FROM "Presupuestos"), 1))
            """))
            await session.execute(text("""
                SELECT setval(pg_get_serial_sequence('movimientos', 'Id'),
                    GREATEST((SELECT MAX("Id") FROM movimientos), 1))
            """))
            await session.execute(text("""
                SELECT setval(pg_get_serial_sequence('"MaestroUsuarios"', 'id'),
                    GREATEST((SELECT MAX(id) FROM "MaestroUsuarios"), 1))
            """))
        print("Secuencias reseteadas OK")

    await engine.dispose()
    print("\nCarga completa!")


if __name__ == "__main__":
    asyncio.run(main())
