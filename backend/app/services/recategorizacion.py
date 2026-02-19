"""
Servicio de recategorización automática de movimientos.
Ejecuta jobs PENDING y actualiza movimientos por ReglaComercioId.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List, Optional

from app.db.job_recategorizacion import (
    create_job,
    get_job,
    list_jobs,
    mark_done,
    mark_failed,
    mark_running,
    reset_for_retry,
)
from app.db.movimientos import recategorize_by_regla
from app.db.regla_comercio import get_regla_by_id

logger = logging.getLogger(__name__)


def enqueue_recategorization_job(
    id_usuario: int,
    regla_comercio_id: int,
    days_back: int = 30,
) -> dict:
    """
    Crea job PENDING para recategorizar movimientos de los últimos N días.
    Retorna el job creado. El worker debe procesarlo (BackgroundTasks o queue).
    """
    since_date = date.today() - timedelta(days=days_back)
    job = create_job(id_usuario, regla_comercio_id, since_date)
    logger.info("JobRecategorizacion creado: id=%s regla=%s usuario=%s", job["id"], regla_comercio_id, id_usuario)
    return job


def process_job(id_usuario: int, job_id: int) -> dict:
    """
    Procesa un job PENDING: marca RUNNING, ejecuta UPDATE, marca DONE/FAILED.
    Retorna {status, updatedRows, error?}.
    """
    job = get_job(id_usuario, job_id)
    if not job:
        return {"status": "NOT_FOUND", "updatedRows": 0}

    if job["status"] != "PENDING":
        return {"status": job["status"], "updatedRows": job.get("updatedRows", 0)}

    if not mark_running(id_usuario, job_id):
        return {"status": "ALREADY_RUNNING", "updatedRows": 0}

    regla = get_regla_by_id(id_usuario, job["reglaComercioId"])
    if not regla:
        mark_failed(id_usuario, job_id, "Regla no encontrada")
        return {"status": "FAILED", "updatedRows": 0, "error": "Regla no encontrada"}

    id_cat = int(regla["idCategoria"])
    id_sub = int(regla["idSubcategoria"])
    since_date = date.fromisoformat(job["sinceDate"]) if job["sinceDate"] else date.today() - timedelta(days=30)

    try:
        updated = recategorize_by_regla(
            id_usuario=id_usuario,
            regla_id=job["reglaComercioId"],
            since_date=since_date,
            id_categoria=id_cat,
            id_subcategoria=id_sub,
        )
        mark_done(id_usuario, job_id, updated)
        logger.info("JobRecategorizacion DONE: id=%s updatedRows=%s", job_id, updated)
        return {"status": "DONE", "updatedRows": updated}
    except Exception as e:
        err_msg = str(e)
        mark_failed(id_usuario, job_id, err_msg)
        logger.exception("JobRecategorizacion FAILED: id=%s error=%s", job_id, err_msg)
        return {"status": "FAILED", "updatedRows": 0, "error": err_msg}


def process_pending_jobs(id_usuario: int) -> List[dict]:
    """
    Procesa todos los jobs PENDING del usuario.
    Retorna lista de resultados.
    """
    jobs = list_jobs(id_usuario, status="PENDING", limit=100)
    return [process_job(id_usuario, j["id"]) for j in jobs]
