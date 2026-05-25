"""
charts.py
---------
POST /session/{session_id}/charts

Applies the same FilterBody as /filter and returns pre-aggregated data
for the four dashboard charts, ready for direct consumption by the frontend.
Called with a debounce of ~400 ms every time filters change.
"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import ChartsResponse, FilterBody
from app.services.catalog_service import catalog_service
from app.services.charts_service import get_charts
from app.services.filter_service import apply_filters
from app.services.session_manager import session_manager

router = APIRouter(prefix="/session/{session_id}", tags=["charts"])


def _load_catalog(column: str) -> dict:
    """Return the label catalog for *column*, or an empty dict if none exists."""
    key = catalog_service.find_catalog_for_column(column)
    if key:
        return catalog_service.get(key) or {}
    return {}


@router.post("/charts", response_model=ChartsResponse)
def get_charts_data(session_id: str, body: FilterBody):
    """
    Return pre-aggregated chart data for the filtered dataset.

    Aggregations
    ~~~~~~~~~~~~
    ``by_institution``  SIGLAS grouped, count + avg VALOR CONCLUIDO (top 12).
    ``by_clase``        CLASE grouped with catalog label, count + avg VALOR CONCLUIDO.
    ``by_grupo``        GRUPO grouped with label, count + avg \\$M2 SV.
    ``scatter``         Random sample ≤ 500 points: SUP CONSTRUIDA vs VALOR CONCLUIDO,
                        colored by CLASE.
    ``total_matching``  Total rows after filters (for KPI cards).
    """
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada")

    filtered = apply_filters(session.df, body.filters, body.search)

    catalogs = {
        col: _load_catalog(col)
        for col in [
            "CLASE",
            "GRUPO",
            "CONSERVACION",
            "ELEVADOR",
            "ID VIGILANCIA",
            "ID AGUA POTABLE",
            "ID SUMINISTRO ELECTRICO",
            "ID TRANSPORTE URBANO",
        ]
    }

    data = get_charts(filtered, catalogs)

    return ChartsResponse(session_id=session_id, **data)
