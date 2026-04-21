"""Endpoints de tracking de jobs de recategorización."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from app.deps import get_current_user_id
from app.db.job_recategorizacion import get_job, list_jobs, reset_for_retry
from app.services.recategorizacion import process_job

router = APIRouter()


@router.get("")
async def list_recategorizaciones(
    status: str | None = Query(default=None, description="PENDING|RUNNING|DONE|FAILED"),
    limit: int = Query(default=50, ge=1, le=200),
    id_usuario: int = Depends(get_current_user_id),
):
    """Lista jobs de recategorización del usuario."""
    jobs = list_jobs(id_usuario, status=status, limit=limit)
    return {"items": jobs, "total": len(jobs)}


@router.get("/{id}")
async def get_recategorizacion(
    id: int,
    id_usuario: int = Depends(get_current_user_id),
):
    job = get_job(id_usuario, id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return job


@router.post("/{id}/retry")
async def retry_recategorizacion(
    id: int,
    background_tasks: BackgroundTasks,
    id_usuario: int = Depends(get_current_user_id),
):
    job = get_job(id_usuario, id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    if job["status"] not in ("FAILED", "PENDING"):
        raise HTTPException(
            status_code=400,
            detail=f"Job en estado {job['status']}, solo se puede reintentar FAILED o PENDING",
        )

    if not reset_for_retry(id_usuario, id):
        raise HTTPException(status_code=400, detail="No se pudo resetear el job")

    background_tasks.add_task(process_job, id_usuario, id)
    return {"ok": True, "id": id, "message": "Job encolado para reprocesamiento"}
