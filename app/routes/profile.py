"""
profile.py
----------
GET /session/{session_id}/profile

Re-runs the full profile on the session's DataFrame.
Useful when the frontend needs a fresh profile after applying filters
or any server-side transformation.
"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import FullProfileResponse
from app.services.profiling_service import full_profile
from app.services.session_manager import session_manager

router = APIRouter(prefix="/session/{session_id}")


@router.get("/profile", response_model=FullProfileResponse)
def get_profile(session_id: str):
    """
    Return a complete profile of the session's dataset.

    The response format is identical to ``POST /upload``, making it easy
    to refresh the dashboard state without re-uploading the file.
    """
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada")

    return full_profile(session.df, session.filename, session_id)

