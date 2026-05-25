from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import DataResponse
from app.services.filter_service import paginate
from app.services.session_manager import session_manager

router = APIRouter(prefix="/session/{session_id}")


@router.get("/data", response_model=DataResponse)
def get_data(
    session_id: str,
    limit: int = Query(default=100, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
):
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada")

    page, total = paginate(session.df, offset, limit)

    return DataResponse(
        session_id=session_id,
        total_rows=total,
        returned=len(page),
        offset=offset,
        data=page.where(page.notna(), None).to_dict(orient="records"),
    )
