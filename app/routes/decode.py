from fastapi import APIRouter, HTTPException

from app.models.schemas import DecodeDistributionItem, DecodeResponse
from app.services.catalog_service import catalog_service
from app.services.session_manager import session_manager

router = APIRouter(prefix="/session/{session_id}")


@router.get("/decode/{column}", response_model=DecodeResponse)
def decode_column(session_id: str, column: str, catalog_key: str | None = None):
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada")

    if column not in session.df.columns:
        raise HTTPException(status_code=404, detail=f"Columna '{column}' no encontrada en el dataset")

    resolved_key = catalog_key or catalog_service.find_catalog_for_column(column)
    if not resolved_key:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró catálogo para la columna '{column}'. Especifica catalog_key.",
        )

    catalog = catalog_service.get(resolved_key)
    if not catalog:
        raise HTTPException(status_code=404, detail=f"Catálogo '{resolved_key}' no existe")

    total = len(session.df)
    value_counts = session.df[column].value_counts(dropna=False)

    distribution = []
    for raw_code, count in value_counts.items():
        label = catalog_service.decode_value(resolved_key, raw_code)
        distribution.append(
            DecodeDistributionItem(
                code=str(raw_code),
                label=label,
                count=int(count),
                pct=round(count / max(total, 1) * 100, 2),
            )
        )

    return DecodeResponse(column=column, catalog_key=resolved_key, distribution=distribution)
