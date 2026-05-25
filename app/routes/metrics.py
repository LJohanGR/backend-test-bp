from fastapi import APIRouter, HTTPException

from app.models.schemas import MetricsResponse
from app.services.metrics_service import get_metrics
from app.services.session_manager import session_manager

router = APIRouter(prefix="/session/{session_id}")


@router.get("/metrics", response_model=MetricsResponse)
def get_session_metrics(session_id: str):
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada")

    metrics = get_metrics(session.df)
    return MetricsResponse(session_id=session_id, **metrics)
