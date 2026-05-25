"""
upload.py
---------
POST /upload

Accepts a CSV file, validates it, stores the DataFrame in a session,
and immediately returns a full dataset profile so the frontend can
render a dashboard without a second round-trip.
"""

import io

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.models.schemas import FullProfileResponse
from app.services.profiling_service import full_profile
from app.services.session_manager import session_manager

router = APIRouter()

_MAX_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024


@router.post("/upload", response_model=FullProfileResponse)
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file and receive a complete profile in a single response.

    - Creates a server-side session (returned as ``session_id``).
    - Validates file type and size.
    - Returns per-column statistics, suggested dashboard filters, and
      decoded catalog labels for coded columns.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .csv")

    content = await file.read()

    if len(content) > _MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Archivo demasiado grande. Máximo permitido: {settings.MAX_FILE_SIZE_MB} MB",
        )

    try:
        df = pd.read_csv(io.BytesIO(content), low_memory=False)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"No se pudo procesar el CSV: {exc}",
        ) from exc

    if df.empty:
        raise HTTPException(status_code=422, detail="El archivo CSV está vacío")

    session_id = session_manager.create(df, file.filename)

    return full_profile(df, file.filename, session_id)

