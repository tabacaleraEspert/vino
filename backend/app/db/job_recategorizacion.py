"""
Repository SQL para JobRecategorizacion (auditoría de recategorización).
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from app.db.connection import get_connection

logger = logging.getLogger(__name__)

STATUS_PENDING = "PENDING"
STATUS_RUNNING = "RUNNING"
STATUS_DONE = "DONE"
STATUS_FAILED = "FAILED"


def create_job(
    id_usuario: int,
    regla_comercio_id: int,
    since_date: date,
) -> Dict[str, Any]:
    """Crea job PENDING. Retorna el registro creado."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dbo.JobRecategorizacion (Id_usuario, ReglaComercioId, SinceDate, Status)
            OUTPUT INSERTED.Id, INSERTED.Id_usuario, INSERTED.ReglaComercioId, INSERTED.SinceDate,
                   INSERTED.Status, INSERTED.UpdatedRows, INSERTED.CreatedAt, INSERTED.UpdatedAt
            VALUES (?, ?, ?, 'PENDING')
            """,
            (id_usuario, regla_comercio_id, since_date),
        )
        row = cur.fetchone()
        conn.commit()

    if not row:
        raise RuntimeError("No se pudo crear el job")

    return {
        "id": row[0],
        "id_usuario": row[1],
        "reglaComercioId": row[2],
        "sinceDate": row[3].strftime("%Y-%m-%d") if row[3] else None,
        "status": row[4],
        "updatedRows": row[5] or 0,
        "createdAt": row[6].isoformat() if row[6] else None,
        "updatedAt": row[7].isoformat() if row[7] else None,
        "error": None,
    }


def get_job(id_usuario: int, job_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene job por Id. Valida Id_usuario."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT Id, Id_usuario, ReglaComercioId, SinceDate, Status, UpdatedRows, Error, CreatedAt, UpdatedAt
            FROM dbo.JobRecategorizacion
            WHERE Id_usuario = ? AND Id = ?
            """,
            (id_usuario, job_id),
        )
        row = cur.fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "id_usuario": row[1],
        "reglaComercioId": row[2],
        "sinceDate": row[3].strftime("%Y-%m-%d") if row[3] else None,
        "status": row[4],
        "updatedRows": row[5] or 0,
        "error": row[6],
        "createdAt": row[7].isoformat() if row[7] else None,
        "updatedAt": row[8].isoformat() if row[8] else None,
    }


def list_jobs(
    id_usuario: int,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Lista jobs del usuario. Filtro opcional por status."""
    with get_connection() as conn:
        cur = conn.cursor()
        if status:
            cur.execute(
                """
                SELECT Id, Id_usuario, ReglaComercioId, SinceDate, Status, UpdatedRows, Error, CreatedAt, UpdatedAt
                FROM dbo.JobRecategorizacion
                WHERE Id_usuario = ? AND Status = ?
                ORDER BY CreatedAt DESC
                OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
                """,
                (id_usuario, status.strip(), limit),
            )
        else:
            cur.execute(
                """
                SELECT Id, Id_usuario, ReglaComercioId, SinceDate, Status, UpdatedRows, Error, CreatedAt, UpdatedAt
                FROM dbo.JobRecategorizacion
                WHERE Id_usuario = ?
                ORDER BY CreatedAt DESC
                OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
                """,
                (id_usuario, limit),
            )
        rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "id_usuario": r[1],
            "reglaComercioId": r[2],
            "sinceDate": r[3].strftime("%Y-%m-%d") if r[3] else None,
            "status": r[4],
            "updatedRows": r[5] or 0,
            "error": r[6],
            "createdAt": r[7].isoformat() if r[7] else None,
            "updatedAt": r[8].isoformat() if r[8] else None,
        }
        for r in rows
    ]


def mark_running(id_usuario: int, job_id: int) -> bool:
    """Marca job como RUNNING."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE dbo.JobRecategorizacion
            SET Status = 'RUNNING', UpdatedAt = SYSUTCDATETIME()
            WHERE Id_usuario = ? AND Id = ? AND Status = 'PENDING'
            """,
            (id_usuario, job_id),
        )
        conn.commit()
        return cur.rowcount > 0


def mark_done(id_usuario: int, job_id: int, updated_rows: int) -> bool:
    """Marca job como DONE con filas actualizadas."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE dbo.JobRecategorizacion
            SET Status = 'DONE', UpdatedRows = ?, UpdatedAt = SYSUTCDATETIME()
            WHERE Id_usuario = ? AND Id = ?
            """,
            (updated_rows, id_usuario, job_id),
        )
        conn.commit()
        return cur.rowcount > 0


def mark_failed(id_usuario: int, job_id: int, error: str) -> bool:
    """Marca job como FAILED con mensaje de error."""
    err_trunc = (error or "")[:2000]
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE dbo.JobRecategorizacion
            SET Status = 'FAILED', Error = ?, UpdatedAt = SYSUTCDATETIME()
            WHERE Id_usuario = ? AND Id = ?
            """,
            (err_trunc, id_usuario, job_id),
        )
        conn.commit()
        return cur.rowcount > 0


def reset_for_retry(id_usuario: int, job_id: int) -> bool:
    """Resetea job FAILED o PENDING a PENDING para retry."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE dbo.JobRecategorizacion
            SET Status = 'PENDING', Error = NULL, UpdatedRows = 0, UpdatedAt = SYSUTCDATETIME()
            WHERE Id_usuario = ? AND Id = ? AND Status IN ('FAILED', 'PENDING')
            """,
            (id_usuario, job_id),
        )
        conn.commit()
        return cur.rowcount > 0
