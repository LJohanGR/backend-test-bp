"""
charts_service.py
-----------------
Computes pre-aggregated chart data from an (already-filtered) DataFrame.

Column mapping — real dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``SIGLAS``          → by_institution (valuation unit abbreviation, 31 unique)
``CLASE``           → by_clase       (property class code, numeric 0-8)
``GRUPO``           → by_grupo       (lender group: ONAVIS, BANCOS, …)
``VALOR CONCLUIDO`` → avg_valor      (final appraised value)
``$M2 SV``         → avg_m2         (value per square metre)
``SUP CONSTRUIDA``  → scatter x-axis (built area in m²)

All columns are treated as optional; aggregations that reference a missing
column are simply omitted from the output.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from app.utils.dataframe_utils import agg_records, code_str, iso_week_label, parse_dates, safe_float

# ── Column names (real dataset) ──────────────────────────────────────────────
_COL_INSTITUTION = "SIGLAS"
_COL_CLASE       = "CLASE"
_COL_GRUPO       = "GRUPO"
_COL_VALOR       = "VALOR CONCLUIDO"
_COL_M2          = "$M2 SV"
_COL_SUP         = "SUP CONSTRUIDA"

# Columns used by the new charts
_COL_FECHA        = "FECHA AVALUO"
_COL_EDAD         = "EDAD MESES"
_COL_CONSERVACION = "CONSERVACION"
_COL_ELEVADOR     = "ELEVADOR"
_COL_VIGILANCIA   = "ID VIGILANCIA"
_COL_AGUA         = "ID AGUA POTABLE"
_COL_ELECTRICO    = "ID SUMINISTRO ELECTRICO"
_COL_TRANSPORTE   = "ID TRANSPORTE URBANO"

_MAX_INSTITUTIONS  = 12
_SCATTER_SAMPLE    = 500
_ANTIGUEDAD_SAMPLE = 500


# ── Per-chart aggregations ───────────────────────────────────────────────────

def _by_institution(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if _COL_INSTITUTION not in df.columns:
        return []

    extra: Dict[str, Any] = {}
    if _COL_VALOR in df.columns:
        extra["avg_valor"] = (_COL_VALOR, "mean")

    records = agg_records(df, _COL_INSTITUTION, extra)

    return [
        {
            "name":      str(r[_COL_INSTITUTION]),
            "count":     int(r["count"]),
            "avg_valor": safe_float(r.get("avg_valor", 0)),
        }
        for r in records[:_MAX_INSTITUTIONS]
    ]


def _by_clase(
    df: pd.DataFrame,
    catalog: Dict[str, str],
) -> List[Dict[str, Any]]:
    if _COL_CLASE not in df.columns:
        return []

    extra: Dict[str, Any] = {}
    if _COL_VALOR in df.columns:
        extra["avg_valor"] = (_COL_VALOR, "mean")

    records = agg_records(df, _COL_CLASE, extra)

    result = []
    for r in records:
        code = code_str(r[_COL_CLASE])
        result.append({
            "code":      code,
            "label":     catalog.get(code, code),
            "count":     int(r["count"]),
            "avg_valor": safe_float(r.get("avg_valor", 0)),
        })
    return result


def _by_grupo(
    df: pd.DataFrame,
    catalog: Dict[str, str],
) -> List[Dict[str, Any]]:
    if _COL_GRUPO not in df.columns:
        return []

    extra: Dict[str, Any] = {}
    if _COL_M2 in df.columns:
        extra["avg_m2"] = (_COL_M2, "mean")

    records = agg_records(df, _COL_GRUPO, extra)

    result = []
    for r in records:
        code = str(r[_COL_GRUPO])
        result.append({
            "code":    code,
            "label":   catalog.get(code, code),   # GRUPO values are already readable strings
            "count":   int(r["count"]),
            "avg_m2":  safe_float(r.get("avg_m2", 0)),
        })
    return result


def _scatter(df: pd.DataFrame) -> List[Dict[str, Any]]:
    needed = [_COL_SUP, _COL_VALOR]
    if not all(c in df.columns for c in needed):
        return []

    cols = needed + ([_COL_CLASE] if _COL_CLASE in df.columns else [])
    sub = df[cols].copy()
    sub[_COL_SUP]   = pd.to_numeric(sub[_COL_SUP],   errors="coerce")
    sub[_COL_VALOR] = pd.to_numeric(sub[_COL_VALOR], errors="coerce")
    sub = sub.dropna(subset=needed)

    if len(sub) > _SCATTER_SAMPLE:
        sub = sub.sample(_SCATTER_SAMPLE, random_state=42)

    result = []
    for r in sub.to_dict(orient="records"):
        result.append({
            "x":     safe_float(r[_COL_SUP]),
            "y":     safe_float(r[_COL_VALOR]),
            "clase": code_str(r[_COL_CLASE]) if _COL_CLASE in r else "",
        })
    return result


# ── Public entry point ───────────────────────────────────────────────────────

# ── Temporal evolution (line chart) ─────────────────────────────────────────

def _temporal(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Weekly aggregation of VALOR CONCLUIDO for the line chart.

    Groups rows by ISO year-week (``YYYY-WXX``) and returns one record
    per week sorted chronologically.  Uses ``iso_week_label`` from utils
    to correctly handle year-boundary weeks.
    """
    if _COL_FECHA not in df.columns:
        return []

    cols = [_COL_FECHA] + ([_COL_VALOR] if _COL_VALOR in df.columns else [])
    tmp = df[cols].copy()
    tmp["_date"] = parse_dates(tmp[_COL_FECHA])
    tmp = tmp.dropna(subset=["_date"])
    if tmp.empty:
        return []

    tmp["_semana"] = iso_week_label(tmp["_date"])

    agg_spec: Dict[str, Any] = {"count": ("_semana", "count")}
    if _COL_VALOR in tmp.columns:
        agg_spec["avg_valor"]   = (_COL_VALOR, "mean")
        agg_spec["total_valor"] = (_COL_VALOR, "sum")

    records = (
        tmp.groupby("_semana")
        .agg(**agg_spec)
        .reset_index()
        .sort_values("_semana")
        .to_dict(orient="records")
    )

    return [
        {
            "periodo":     str(r["_semana"]),
            "count":       int(r["count"]),
            "avg_valor":   safe_float(r.get("avg_valor", 0)),
            "total_valor": safe_float(r.get("total_valor", 0)),
        }
        for r in records
    ]


# ── Antigüedad vs valor (scatter) ────────────────────────────────────────────

def _antiguedad_scatter(
    df: pd.DataFrame,
    conservacion_catalog: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Scatter: EDAD MESES vs VALOR CONCLUIDO / $M2 SV, coloured by CONSERVACION."""
    if _COL_EDAD not in df.columns:
        return []

    available = [_COL_EDAD]
    for col in (_COL_VALOR, _COL_M2, _COL_CONSERVACION):
        if col in df.columns:
            available.append(col)

    sub = df[available].copy()
    sub[_COL_EDAD] = pd.to_numeric(sub[_COL_EDAD], errors="coerce")
    sub = sub.dropna(subset=[_COL_EDAD])

    if len(sub) > _ANTIGUEDAD_SAMPLE:
        sub = sub.sample(_ANTIGUEDAD_SAMPLE, random_state=42)

    result = []
    for r in sub.to_dict(orient="records"):
        code = code_str(r[_COL_CONSERVACION]) if _COL_CONSERVACION in r else ""
        result.append({
            "edad_meses":      safe_float(r[_COL_EDAD]),
            "valor_concluido": safe_float(r.get(_COL_VALOR, 0)),
            "precio_m2":       safe_float(r.get(_COL_M2, 0)),
            "conservacion":    conservacion_catalog.get(code, code) if code else "",
        })
    return result


# ── Public entry point ───────────────────────────────────────────────────────

def get_charts(
    df: pd.DataFrame,
    catalogs: Dict[str, Dict[str, str]],
) -> Dict[str, Any]:
    """
    Return pre-aggregated chart data for *df* (already filtered).

    *catalogs* should contain label mappings keyed by column name
    (e.g. ``{"CLASE": {"1": "Mínima", "2": "Económica", ...}}``).
    Missing catalog entries fall back to the raw code value.
    """
    return {
        "total_matching": len(df),
        "by_institution": _by_institution(df),
        "by_clase":       _by_clase(df, catalogs.get(_COL_CLASE, {})),
        "by_grupo":       _by_grupo(df, catalogs.get(_COL_GRUPO, {})),
        "scatter":        _scatter(df),
        "temporal":          _temporal(df),
        "antiguedad_scatter": _antiguedad_scatter(df, catalogs.get(_COL_CONSERVACION, {})),
    }
