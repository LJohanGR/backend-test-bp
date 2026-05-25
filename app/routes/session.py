from fastapi import APIRouter, HTTPException

from app.models.schemas import SessionInfo
from app.services.session_manager import session_manager

router = APIRouter(prefix="/session/{session_id}")


@router.get("", response_model=SessionInfo)
def get_session(session_id: str):
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada")
    return SessionInfo(
        session_id=session_id,
        filename=session.filename,
        row_count=len(session.df),
        column_count=len(session.df.columns),
        created_at=session.created_at.isoformat(),
        expires_at=session.expires_at.isoformat(),
    )


@router.delete("")
def delete_session(session_id: str):
    deleted = session_manager.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return {"detail": "Sesión eliminada"}
