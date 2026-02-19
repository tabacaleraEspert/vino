"""
Endpoints de tracking de jobs de recategorización.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from app.core.security import require_user
from app.db.catalog import _get_id_usuario
from app.db.job_recategorizacion import get_job, list_jobs, reset_for_retry
from app.services.recategorizacion import process_job

router = APIRouter()


@router.get("")
def list_recategorizaciones(
    status: str | None = Query(default=None, description="PENDING|RUNNING|DONE|FAILED"),
    limit: int = Query(default=50, ge=1, le=200),
    user: dict = Depends(require_user),
):
    """Lista jobs de recategorización del usuario."""
    try:
        id_usuario = _get_id_usuario(user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    jobs = list_jobs(id_usuario, status=status, limit=limit)
    return {
        "items": jobs,
        "total": len(jobs),
    }


@router.get("/{id}")
def get_recategorizacion(id: str, user: dict = Depends(require_user)):
    """Obtiene un job por Id."""
    try:
        id_usuario = _get_id_usuario(user)
        job_id = int(id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Job no encontrado")

    job = get_job(id_usuario, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return job


@router.post("/{id}/retry")
def retry_recategorizacion(id: str, background_tasks: BackgroundTasks, user: dict = Depends(require_user)):
    """Reintenta un job FAILED o PENDING."""
    try:
        id_usuario = _get_id_usuario(user)
        job_id = int(id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Job no encontrado")

    job = get_job(id_usuario, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    if job["status"] not in ("FAILED", "PENDING"):
        raise HTTPException(
            status_code=400,
            detail=f"Job en estado {job['status']}, solo se puede reintentar FAILED o PENDING",
        )

    if not reset_for_retry(id_usuario, job_id):
        raise HTTPException(status_code=400, detail="No se pudo resetear el job")

    background_tasks.add_task(process_job, id_usuario, job_id)
    return {"ok": True, "id": job_id, "message": "Job encolado para reprocesamiento"}
