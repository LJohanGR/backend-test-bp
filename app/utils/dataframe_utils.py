"""
dataframe_utils.py
------------------
Stateless helpers for DataFrame operations shared across services.

Exported
~~~~~~~~
``safe_float``      Convert any value to float; 0.0 on NaN / error.
``code_str``        Normalise a categorical code to a plain string.
``agg_records``     groupby + named-agg → sorted list of dicts.
``parse_dates``     Parse a date Series robustly (dayfirst=True).
``iso_week_label``  Convert a datetime Series to "YYYY-WXX" labels.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

# String values that should be treated as missing when a column is cast to str
NULLISH: frozenset[str] = frozenset({"nan", "none", "nat", "<na>", ""})


def safe_float(val: Any) -> float:
    """Return *val* as a float (2 dp); 0.0 on NaN or conversion error."""
    try:
        v = float(val)
        return round(v, 2) if v == v else 0.0   # v == v is False for NaN
    except (TypeError, ValueError):
        return 0.0


def code_str(val: Any) -> str:
    """
    Normalise a categorical code to a plain string.

    int-like floats (e.g. ``3.0``) are rendered as ``"3"`` rather than
    ``"3.0"`` so they match catalog keys consistently.
    """
    if isinstance(val, float) and val == val:   # not NaN
        return str(int(val))
    return str(val)


def agg_records(
    df: pd.DataFrame,
    group_col: str,
    extra_aggs: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Group *df* by *group_col*, apply named aggregations, and return the
    result as a list of plain dicts sorted by ``count`` descending.

    ``extra_aggs`` uses the pandas named-agg tuple syntax::

        {"avg_valor": ("VALOR CONCLUIDO", "mean")}
    """
    agg_spec: Dict[str, Any] = {"count": (group_col, "count"), **extra_aggs}
    return (
        df.groupby(group_col, dropna=True)
        .agg(**agg_spec)
        .reset_index()
        .sort_values("count", ascending=False)
        .to_dict(orient="records")
    )


def parse_dates(series: pd.Series) -> pd.Series:
    """
    Parse a Series of date strings to ``datetime64``.

    Uses ``dayfirst=True`` to handle DD/MM/YYYY formats common in
    Mexican government datasets.  Unparseable values become ``NaT``.
    """
    return pd.to_datetime(series, errors="coerce", dayfirst=True)


def iso_week_label(date_series: pd.Series) -> pd.Series:
    """
    Convert a datetime Series to ISO year-week labels (``YYYY-WXX``).

    Uses ``dt.isocalendar()`` for correctness at year boundaries, where
    the first/last days of a calendar year can belong to the adjacent
    ISO year's week.

    Example::

        2024-01-01  →  "2023-W52"   (belongs to the last week of 2023)
        2024-01-08  →  "2024-W02"
    """
    iso = date_series.dt.isocalendar()          # DataFrame: year, week, day
    return (
        iso["year"].astype(str)
        + "-W"
        + iso["week"].astype(str).str.zfill(2)
    )
