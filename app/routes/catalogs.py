from fastapi import APIRouter

from app.models.schemas import CatalogInfo
from app.services.catalog_service import catalog_service

router = APIRouter()


@router.get("/catalogs", response_model=CatalogInfo)
def get_catalogs():
    """Retorna todos los catálogos cargados al inicio del servidor."""
    return CatalogInfo(catalogs=catalog_service.get_all())
