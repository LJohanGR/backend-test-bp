from fastapi import APIRouter, HTTPException

from app.models.schemas import FilterBody, FilterResponse
from app.services.filter_service import apply_filters, paginate
from app.services.session_manager import session_manager

router = APIRouter(prefix="/session/{session_id}")


@router.post("/filter", response_model=FilterResponse)
def filter_data(session_id: str, body: FilterBody):
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada")

    filtered = apply_filters(session.df, body.filters, body.search)
    page, total = paginate(filtered, body.offset, body.limit)

    return FilterResponse(
        session_id=session_id,
        total_matching=total,
        returned=len(page),
        offset=body.offset,
        data=page.where(page.notna(), None).to_dict(orient="records"),
    )
