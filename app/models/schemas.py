from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Profile models
# ---------------------------------------------------------------------------

class HistogramData(BaseModel):
    """Bin edges (len = bins+1) and counts (len = bins) for a numeric column."""
    edges: List[float]
    counts: List[int]


class Percentiles(BaseModel):
    p25: float
    p50: float
    p75: float


class NumericColumnStats(BaseModel):
    """Statistics returned for numeric columns (continuous or high-cardinality int)."""
    type: str = "numeric"
    n_unique: int
    n_missing: int
    pct_missing: float
    mean: Optional[float] = None
    std: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    percentiles: Optional[Percentiles] = None
    histogram: Optional[HistogramData] = None
    catalog_key: Optional[str] = None


class CategoricalColumnStats(BaseModel):
    """Statistics for categorical columns (low-cardinality or coded values)."""
    type: str = "categorical"
    n_unique: int
    n_missing: int
    pct_missing: float
    value_counts: Dict[str, int]
    catalog_key: Optional[str] = None


class DatetimeColumnStats(BaseModel):
    """Statistics for date/datetime columns."""
    type: str = "date"
    n_unique: int
    n_missing: int
    pct_missing: float
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    catalog_key: Optional[str] = None


class TextColumnStats(BaseModel):
    """Statistics for high-cardinality string columns."""
    type: str = "text"
    n_unique: int
    n_missing: int
    pct_missing: float
    top_values: List[Dict[str, Any]]
    catalog_key: Optional[str] = None


class FilterColumnMeta(BaseModel):
    """Metadata for a single column within a priority filter group."""
    column: str
    label: str
    filter_type: str  # "select" | "range" | "search" | "date_range"
    n_unique: int
    has_catalog: bool = False
    min: Optional[float] = None
    max: Optional[float] = None


class FilterGroupMeta(BaseModel):
    """A logical group of related filter columns (e.g. 'Ubicación')."""
    label: str
    columns: List[FilterColumnMeta]


class FullProfileResponse(BaseModel):
    """
    Complete dataset profile returned by POST /upload and GET /session/{id}/profile.

    - ``shape``: [rows, columns]
    - ``duplicates_count``: number of fully-duplicated rows
    - ``memory_mb``: approximate in-memory size of the dataset
    - ``suggested_filters``: flat ordered list of priority filter column names
    - ``filter_groups``: structured priority filters grouped by business category
    - ``columns``: per-column statistics (type-specific payload)
    - ``catalogs``: decoded lookup tables keyed by column name (file + derived)
    """
    session_id: str
    filename: str
    shape: List[int]
    duplicates_count: int
    memory_mb: float
    suggested_filters: List[str]
    filter_groups: Dict[str, FilterGroupMeta]
    columns: Dict[str, Any]
    catalogs: Dict[str, Dict[str, str]]


class SessionInfo(BaseModel):
    session_id: str
    filename: str
    row_count: int
    column_count: int
    created_at: str
    expires_at: str


class MetricsResponse(BaseModel):
    session_id: str
    total_rows: int
    total_columns: int
    null_summary: Dict[str, float]
    numeric_columns: List[str]
    categorical_columns: List[str]
    datetime_columns: List[str]


class FilterBody(BaseModel):
    filters: Dict[str, Any] = {}   # str[] para categórico | {min?, max?} para numérico
    search: Optional[str] = None   # búsqueda libre en columnas de texto
    limit: int = 100
    offset: int = 0


class FilterResponse(BaseModel):
    session_id: str
    total_matching: int
    returned: int
    offset: int
    data: List[Dict[str, Any]]


class DataResponse(BaseModel):
    session_id: str
    total_rows: int
    returned: int
    offset: int
    data: List[Dict[str, Any]]


class MapDataResponse(BaseModel):
    session_id: str
    lat_column: Optional[str]
    lon_column: Optional[str]
    features: List[Dict[str, Any]]


class CatalogInfo(BaseModel):
    catalogs: Dict[str, Dict[str, str]]


class DecodeDistributionItem(BaseModel):
    code: str
    label: str
    count: int
    pct: float


class DecodeResponse(BaseModel):
    column: str
    catalog_key: str
    distribution: List[DecodeDistributionItem]


# ---------------------------------------------------------------------------
# Charts models
# ---------------------------------------------------------------------------

class ByInstitutionItem(BaseModel):
    name: str
    count: int
    avg_valor: float


class ByClaseItem(BaseModel):
    code: str
    label: str
    avg_valor: float
    count: int


class ByGrupoItem(BaseModel):
    code: str
    label: str
    avg_m2: float
    count: int


class ScatterPoint(BaseModel):
    x: float
    y: float
    clase: str


class ChartsResponse(BaseModel):
    session_id: str
    total_matching: int
    by_institution: List[ByInstitutionItem]
    by_clase: List[ByClaseItem]
    by_grupo: List[ByGrupoItem]
    scatter: List[ScatterPoint]
    temporal: List["TemporalPoint"]
    antiguedad_scatter: List["AntiguedadPoint"]


class TemporalPoint(BaseModel):
    periodo: str        # "YYYY-WXX"  (ISO year-week, e.g. "2024-W03")
    count: int
    avg_valor: float
    total_valor: float


class AntiguedadPoint(BaseModel):
    edad_meses: float
    valor_concluido: float
    precio_m2: float
    conservacion: str   # decoded label from catalog


class DistItem(BaseModel):
    label: str
    count: int
    pct: float          # percentage (0–100)


class EstacionamientoItem(BaseModel):
    tipo: str           # column name (e.g. "ESTACIONAMIENTO CUBIERTO")
    promedio: float




# Resolve forward references
ChartsResponse.model_rebuild()


# ---------------------------------------------------------------------------
# KPIs model
# ---------------------------------------------------------------------------

class KPIsResponse(BaseModel):
    session_id: str
    total_matching: int
    avg_valor_concluido: float
    avg_sup_construida: float
    avg_precio_m2: float
    total_valor_portafolio: float
    avg_edad_anios: float
