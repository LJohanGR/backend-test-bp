"""
kpis.py
-------
POST /session/{session_id}/kpis

Applies the same FilterBody as /charts and returns five scalar KPIs
about the matching properties.
"""

from fastapi import APIRouter, HTTPException

import pandas as pd

from app.models.schemas import FilterBody, KPIsResponse
from app.services.filter_service import apply_filters
from app.services.session_manager import session_manager

router = APIRouter(prefix="/session/{session_id}", tags=["kpis"])

# Column name constants
_COL_VALOR = "VALOR CONCLUIDO"
_COL_SUP   = "SUP CONSTRUIDA"
_COL_M2    = "$M2 SV"
_COL_EDAD  = "EDAD MESES"


def _agg(df: pd.DataFrame, col: str, func: str) -> float:
    """Apply *func* ('mean' | 'sum') on *col*, returning 0.0 when missing or all-NaN."""
    if col not in df.columns:
        return 0.0
    series = pd.to_numeric(df[col], errors="coerce")
    val = series.mean() if func == "mean" else series.sum()
    # NaN != NaN is True — safe NaN guard
    return round(float(val), 4) if val == val else 0.0


@router.post("/kpis", response_model=KPIsResponse)
def get_kpis(session_id: str, body: FilterBody):
    """
    Return five scalar KPIs calculated over the filtered dataset.

    | Campo                  | Cálculo                          |
    |------------------------|----------------------------------|
    | avg_valor_concluido    | mean(VALOR CONCLUIDO)            |
    | avg_sup_construida     | mean(SUP CONSTRUIDA)             |
    | avg_precio_m2          | mean($M2 SV)                     |
    | total_valor_portafolio | sum(VALOR CONCLUIDO)             |
    | avg_edad_anios         | mean(EDAD MESES) / 12            |
    """
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada")

    df = apply_filters(session.df, body.filters, body.search)

    edad_meses = _agg(df, _COL_EDAD, "mean")

    return KPIsResponse(
        session_id=session_id,
        total_matching=len(df),
        avg_valor_concluido=_agg(df, _COL_VALOR, "mean"),
        avg_sup_construida=_agg(df, _COL_SUP, "mean"),
        avg_precio_m2=_agg(df, _COL_M2, "mean"),
        total_valor_portafolio=_agg(df, _COL_VALOR, "sum"),
        avg_edad_anios=round(edad_meses / 12, 4) if edad_meses else 0.0,
    )
