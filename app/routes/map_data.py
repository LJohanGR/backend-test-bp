from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import FilterBody, MapDataResponse
from app.services.filter_service import apply_filters
from app.services.session_manager import session_manager

router = APIRouter(prefix="/session/{session_id}", tags=["map"])

_LAT_CANDIDATES = ["lat", "latitude", "latitud", "y"]
_LON_CANDIDATES = ["lon", "long", "longitude", "longitud", "x"]


def _find_coord_column(columns: List[str], candidates: List[str]) -> Optional[str]:
    cols_lower = {c.lower(): c for c in columns}
    for candidate in candidates:
        if candidate in cols_lower:
            return cols_lower[candidate]
    return None


def _build_features(
    df: pd.DataFrame,
    lat_col: Optional[str],
    lon_col: Optional[str],
    limit: int,
) -> tuple[str, str, List[Dict[str, Any]]]:
    """
    Resolve coordinate columns, drop rows with missing coords, and return
    (resolved_lat, resolved_lon, flat_feature_dicts).

    Features are flat dicts containing **all** columns; the frontend uses
    ``lat_column`` / ``lon_column`` from the response to extract coordinates.
    """
    columns = list(df.columns)
    resolved_lat = lat_col or _find_coord_column(columns, _LAT_CANDIDATES)
    resolved_lon = lon_col or _find_coord_column(columns, _LON_CANDIDATES)

    if not resolved_lat or not resolved_lon:
        raise HTTPException(
            status_code=422,
            detail=(
                "No se encontraron columnas de coordenadas. "
                "Usa lat_col / lon_col para especificarlas."
            ),
        )

    for col in (resolved_lat, resolved_lon):
        if col not in df.columns:
            raise HTTPException(status_code=422, detail=f"Columna '{col}' no existe en el dataset")

    # Ensure coordinate columns are numeric before dropping NaN
    geo_df = df.copy()
    geo_df[resolved_lat] = pd.to_numeric(geo_df[resolved_lat], errors="coerce")
    geo_df[resolved_lon] = pd.to_numeric(geo_df[resolved_lon], errors="coerce")

    geo_df = (
        geo_df.dropna(subset=[resolved_lat, resolved_lon])
        .head(limit)
    )

    features: List[Dict[str, Any]] = geo_df.where(geo_df.notna(), None).to_dict(orient="records")
    return resolved_lat, resolved_lon, features


# ── GET /map-data ─────────────────────────────────────────────────────────────

@router.get("/map-data", response_model=MapDataResponse)
def get_map_data(
    session_id: str,
    lat_col: Optional[str] = Query(default=None),
    lon_col: Optional[str] = Query(default=None),
    limit: int = Query(default=5000, ge=1, le=50000),
):
    """Return map features for the full session dataset (no filters)."""
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada")

    resolved_lat, resolved_lon, features = _build_features(
        session.df, lat_col, lon_col, limit
    )

    return MapDataResponse(
        session_id=session_id,
        lat_column=resolved_lat,
        lon_column=resolved_lon,
        features=features,
    )


# ── POST /map-data ────────────────────────────────────────────────────────────

@router.post("/map-data", response_model=MapDataResponse)
def post_map_data(
    session_id: str,
    body: FilterBody,
    lat_col: Optional[str] = Query(default=None),
    lon_col: Optional[str] = Query(default=None),
):
    """
    Return map features for the **filtered** dataset.

    Accepts the same ``FilterBody`` as ``POST /filter``
    (categorical list, numeric range, free-text search).
    Use ``body.limit`` to cap the number of features returned (default 5000).
    """
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada")

    filtered = apply_filters(session.df, body.filters, body.search)

    resolved_lat, resolved_lon, features = _build_features(
        filtered, lat_col, lon_col, body.limit
    )

    return MapDataResponse(
        session_id=session_id,
        lat_column=resolved_lat,
        lon_column=resolved_lon,
        features=features,
    )
