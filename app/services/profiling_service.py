"""
profiling_service.py
--------------------
Generates a comprehensive, dashboard-ready profile of a pandas DataFrame.

Public API
~~~~~~~~~~
- ``full_profile(df, filename, session_id) -> dict``
    Entry point called by the upload and profile routes.
    Returns a dict that matches ``FullProfileResponse``.

Column type inference
~~~~~~~~~~~~~~~~~~~~~
+-------------------+----------------------------------------------+
| Inferred type     | Condition                                    |
+===================+==============================================+
| ``datetime``      | pandas datetime dtype, or parseable string   |
+-------------------+----------------------------------------------+
| ``categorical``   | numeric with ≤ 20 unique values, or          |
|                   | object/str with ≤ 50 unique values           |
+-------------------+----------------------------------------------+
| ``numeric``       | numeric with > 20 unique values              |
+-------------------+----------------------------------------------+
| ``text``          | object/str with > 50 unique values           |
+-------------------+----------------------------------------------+

Suggested filters
~~~~~~~~~~~~~~~~~
A column is suggested as a dashboard filter when:
  - It has a matching catalog entry, OR
  - Its unique-value count is between 1 and 50 (inclusive)
Results are capped at ``_MAX_SUGGESTED`` and sorted by
(has_catalog DESC, n_unique ASC).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.services.catalog_service import catalog_service

# ── Tunables ────────────────────────────────────────────────────────────────
_CATEGORICAL_INT_MAX_UNIQUE = 20     # int columns with ≤ this → categorical
_CATEGORICAL_STR_MAX_UNIQUE = 50     # str columns with ≤ this → categorical
_FILTER_MAX_UNIQUE = 50              # upper bound for suggested_filters
_MAX_SUGGESTED = 15                  # cap on suggested_filters list length
_TOP_VALUES_N = 10                   # top-N for text / categorical value_counts
_HISTOGRAM_BINS = 10                 # bins for numeric histograms

# ── Priority filter group definitions ───────────────────────────────────────
# Each entry: (column_name, human_label, filter_type)
# filter_type: "select" | "range" | "search" | "date_range"
_PRIORITY_FILTER_GROUPS: List[Dict[str, Any]] = [
    {
        "key": "ubicacion",
        "label": "Ubicación",
        "columns": [
            ("ID ENTIDAD",   "Estado",          "select"),
        ],
    },
    {
        "key": "tipo_inmueble",
        "label": "Tipo de Inmueble",
        "columns": [
            ("TIPO",               "Tipo de Inmueble",     "select"),
            ("CLASE",              "Clase del Inmueble",   "select"),
            ("CLASE INMUEBLES ZONA", "Clase Zona",         "select"),
        ],
    },
    {
        "key": "conservacion",
        "label": "Estado de Conservación",
        "columns": [
            ("CONSERVACION",        "Estado de Conservación", "select"),
            ("ID CALIDAD PROYECTO", "Calidad del Proyecto",   "select"),
        ],
    },
    {
        "key": "superficie",
        "label": "Superficie (m²)",
        "columns": [
            ("SUP CONSTRUIDA", "Sup. Construida", "range"),
            ("SUP TERRENO",    "Sup. Terreno",    "range"),
            ("SUP VENDIBLE",   "Sup. Vendible",   "range"),
            ("SUP ACCESORIA",  "Sup. Accesoria",  "range"),
        ],
    },
    {
        "key": "valor",
        "label": "Valor ($)",
        "columns": [
            ("VALOR CONCLUIDO",  "Valor Concluido",         "range"),
            ("$M2 SV",           "Valor por m²",            "range"),
            ("VALOR TERRENO M2", "Valor Terreno por m²",    "range"),
            ("VALOR COMPARATIVO","Valor Comparativo",       "range"),
        ],
    },
    {
        "key": "desarrollador",
        "label": "Desarrollador / Unidad Valuadora",
        "columns": [
            ("GRUPO",              "Grupo / Acreditante",         "select"),
            ("SIGLAS",             "Unidad de Valuación (Siglas)", "select"),
            ("Unidad de Valuación","Unidad de Valuación",         "search"),
            ("NOMBRE VP",          "Valuador Profesional",        "search"),
            ("CONSTRUCTOR",        "Constructor / Desarrollador", "search"),
        ],
    },
    {
        "key": "temporal",
        "label": "Período",
        "columns": [
            ("FECHA AVALUO", "Fecha de Avalúo", "date_range"),
            ("AÑO",          "Año",             "select"),
        ],
    },
]

# Columns in the priority list that are numeric but need select treatment
_FORCE_CATEGORICAL_SELECT: set = {
    col_name
    for grp in _PRIORITY_FILTER_GROUPS
    for col_name, _, ft in grp["columns"]
    if ft == "select"
}


# ── Type inference ───────────────────────────────────────────────────────────

def _infer_type(series: pd.Series, n_unique: int) -> str:
    """Return one of: 'numeric', 'categorical', 'datetime', 'text'."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    if pd.api.types.is_numeric_dtype(series):
        return "categorical" if n_unique <= _CATEGORICAL_INT_MAX_UNIQUE else "numeric"

    if series.dtype == object or hasattr(series, "str"):
        # Quick datetime sniff: try common formats on a small sample
        sample = series.dropna().head(200)
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                pd.to_datetime(sample, format=fmt, errors="raise")
                return "datetime"
            except Exception:
                continue
        # Fallback: coerce the full sample and require ≥90 % success
        parsed_pct = pd.to_datetime(sample, errors="coerce").notna().mean()
        if parsed_pct >= 0.9:
            return "datetime"
        return "categorical" if n_unique <= _CATEGORICAL_STR_MAX_UNIQUE else "text"

    return "numeric"


# ── Per-column stats ─────────────────────────────────────────────────────────

def _histogram(series: pd.Series) -> Dict[str, List]:
    counts, edges = np.histogram(series.dropna(), bins=_HISTOGRAM_BINS)
    return {
        "edges": [round(float(e), 4) for e in edges.tolist()],
        "counts": [int(c) for c in counts.tolist()],
    }


def _profile_series(series: pd.Series, total_rows: int) -> Dict[str, Any]:
    """Compute all statistics for a single column."""
    n_missing = int(series.isna().sum())
    pct_missing = round(n_missing / max(total_rows, 1) * 100, 2)
    n_unique = int(series.nunique())
    col_type = _infer_type(series, n_unique)

    # Only categorical columns are eligible for catalog matching
    catalog_key = (
        catalog_service.find_catalog_for_column(str(series.name))
        if col_type == "categorical"
        else None
    )

    base: Dict[str, Any] = {
        "type": col_type,
        "n_unique": n_unique,
        "n_missing": n_missing,
        "pct_missing": pct_missing,
    }
    if catalog_key:
        base["catalog_key"] = catalog_key

    if col_type == "numeric":
        clean = series.dropna()
        if len(clean):
            base.update({
                "mean": round(float(clean.mean()), 4),
                "std": round(float(clean.std()), 4),
                "min": float(clean.min()),
                "max": float(clean.max()),
                "percentiles": {
                    "p25": round(float(clean.quantile(0.25)), 4),
                    "p50": round(float(clean.quantile(0.50)), 4),
                    "p75": round(float(clean.quantile(0.75)), 4),
                },
                "histogram": _histogram(clean),
            })

    elif col_type == "categorical":
        vc = series.value_counts(dropna=True).head(_TOP_VALUES_N)
        base["value_counts"] = {str(k): int(v) for k, v in vc.items()}

    elif col_type == "datetime":
        parsed = pd.to_datetime(series, format="mixed", dayfirst=True, errors="coerce").dropna()
        base["type"] = "date"   # expose as 'date' in the API response
        if len(parsed):
            base["min_date"] = str(parsed.min().date())
            base["max_date"] = str(parsed.max().date())

    elif col_type == "text":
        top = series.value_counts(dropna=True).head(_TOP_VALUES_N)
        base["top_values"] = [{"value": str(k), "count": int(v)} for k, v in top.items()]

    return base


# ── Suggested filters ────────────────────────────────────────────────────────

def _suggest_filters(filter_groups: Dict[str, Any]) -> List[str]:
    """
    Flat ordered list of priority filter column names derived from
    *filter_groups* (select → range → search → date_range, group order).
    """
    seen: set = set()
    result: List[str] = []
    for grp in filter_groups.values():
        for col_meta in grp["columns"]:
            col = col_meta["column"]
            if col not in seen:
                seen.add(col)
                result.append(col)
    return result


# ── Priority filter group builder ────────────────────────────────────────────

def _build_filter_groups(
    df: pd.DataFrame,
    columns_stats: Dict[str, Any],
    col_catalog_keys: Dict[str, str],
) -> Dict[str, Any]:
    """
    Build the ``filter_groups`` dict grouped by business category.
    Only includes columns that exist in *df*.
    """
    result: Dict[str, Any] = {}
    for grp in _PRIORITY_FILTER_GROUPS:
        cols_meta: List[Dict[str, Any]] = []
        for col_name, col_label, filter_type in grp["columns"]:
            if col_name not in df.columns:
                continue
            stats = columns_stats[col_name]
            meta: Dict[str, Any] = {
                "column":      col_name,
                "label":       col_label,
                "filter_type": filter_type,
                "n_unique":    stats["n_unique"],
                "has_catalog": col_name in col_catalog_keys,
            }
            if filter_type == "range":
                meta["min"] = stats.get("min")
                meta["max"] = stats.get("max")
            cols_meta.append(meta)
        if cols_meta:
            result[grp["key"]] = {
                "label":   grp["label"],
                "columns": cols_meta,
            }
    return result


# ── Public entry point ───────────────────────────────────────────────────────

def full_profile(df: pd.DataFrame, filename: str, session_id: str) -> Dict[str, Any]:
    """
    Build a complete profile dictionary for *df*.

    Returns a dict compatible with ``FullProfileResponse``:

    .. code-block:: json

        {
          "session_id": "...",
          "filename": "...",
          "shape": [rows, cols],
          "duplicates_count": N,
          "memory_mb": N,
          "suggested_filters": ["COL_A", ...],
          "columns": {
              "COL_A": { "type": "categorical", "value_counts": {...}, ... },
              "COL_B": { "type": "numeric", "mean": ..., "histogram": {...}, ... }
          },
          "catalogs": {
              "COL_A": {"1": "Label one", "2": "Label two"}
          }
        }
    """
    rows, cols = df.shape

    # ── Dataset-level metrics
    duplicates_count = int(df.duplicated().sum())
    memory_mb = round(df.memory_usage(deep=True).sum() / 1024 ** 2, 2)

    # ── Per-column profiling
    columns_stats: Dict[str, Any] = {}
    col_catalog_keys: Dict[str, str] = {}

    for col in df.columns:
        stats = _profile_series(df[col], rows)
        columns_stats[col] = stats
        if stats.get("catalog_key"):
            col_catalog_keys[col] = stats["catalog_key"]

    # ── Enrich priority "select" columns that were typed as numeric
    #    (e.g. ID ENTIDAD has 32 unique ints → needs value_counts for dropdowns)
    for col in _FORCE_CATEGORICAL_SELECT:
        if col not in df.columns:
            continue
        stats = columns_stats[col]
        if stats["type"] == "numeric" and "value_counts" not in stats:
            vc = df[col].value_counts(dropna=True)
            stats["value_counts"] = {str(k): int(v) for k, v in vc.items()}
            stats["type"] = "categorical"
            # Re-check catalog now that it's categorical
            if not stats.get("catalog_key"):
                ck = catalog_service.find_catalog_for_column(col)
                if ck:
                    stats["catalog_key"] = ck
                    col_catalog_keys[col] = ck

    # ── Priority filter groups
    filter_groups = _build_filter_groups(df, columns_stats, col_catalog_keys)

    # ── Suggested filters (derived from filter_groups order)
    suggested_filters = _suggest_filters(filter_groups)

    # ── Catalogs keyed by column name (official file catalogs)
    catalogs: Dict[str, Dict[str, str]] = {}
    for col_name, catalog_key in col_catalog_keys.items():
        catalog = catalog_service.get(catalog_key)
        if catalog:
            catalogs[col_name] = catalog

    # ── Derived catalogs: string-categorical priority select columns without
    #    an official catalog file (e.g. GRUPO, SIGLAS)
    for grp in _PRIORITY_FILTER_GROUPS:
        for col_name, _, filter_type in grp["columns"]:
            if filter_type != "select" or col_name not in df.columns:
                continue
            if col_name in catalogs:
                continue  # already has an official catalog
            stats = columns_stats.get(col_name, {})
            vc = stats.get("value_counts", {})
            # Only derive for string columns (not raw numeric codes).
            # In pandas ≥2 strings may be StringDtype, not object.
            if vc and not pd.api.types.is_numeric_dtype(df[col_name]):
                catalogs[col_name] = {k: k for k in sorted(vc.keys())}

    return {
        "session_id": session_id,
        "filename": filename,
        "shape": [rows, cols],
        "duplicates_count": duplicates_count,
        "memory_mb": memory_mb,
        "suggested_filters": suggested_filters,
        "filter_groups": filter_groups,
        "columns": columns_stats,
        "catalogs": catalogs,
    }

