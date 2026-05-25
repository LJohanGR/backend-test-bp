from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def apply_filters(
    df: pd.DataFrame,
    filters: Dict[str, Any],
    search: Optional[str] = None,
) -> pd.DataFrame:
    """
    Apply filters to a DataFrame and return the matching rows.

    Filter value semantics
    ~~~~~~~~~~~~~~~~~~~~~~
    ``list``           → ``isin`` match (categorical multi-select).
                         Values are compared as strings, so int-coded
                         columns work when the frontend sends ["3", "4"].
    ``dict``           → range filter with optional ``min`` / ``max`` keys.
                         Numeric if values are numbers: ``{"min": 500000, "max": 2000000}``.
                         Date range if values are strings: ``{"min": "2024-09-02", "max": "2024-09-03"}``.
    ``search`` (str)   → case-insensitive substring search applied across
                         all non-numeric, non-datetime columns.
    """
    if not filters and not search:
        return df

    mask = pd.Series(True, index=df.index)

    for col, value in filters.items():
        if col not in df.columns:
            continue

        if isinstance(value, dict):
            # Range filter — date if either bound is a string, numeric otherwise
            min_val = value.get("min")
            max_val = value.get("max")
            if min_val is None and max_val is None:
                continue
            if isinstance(min_val, str) or isinstance(max_val, str):
                # Date range filter
                col_dates = pd.to_datetime(
                    df[col], format="mixed", dayfirst=True, errors="coerce"
                )
                if min_val is not None:
                    mask &= col_dates >= pd.to_datetime(min_val)
                if max_val is not None:
                    mask &= col_dates <= pd.to_datetime(max_val)
            else:
                # Numeric range filter
                col_num = pd.to_numeric(df[col], errors="coerce")
                if min_val is not None:
                    mask &= col_num >= float(min_val)
                if max_val is not None:
                    mask &= col_num <= float(max_val)

        elif isinstance(value, list) and value:
            # Multi-select: compare both sides as strings
            str_vals = {str(v) for v in value}
            mask &= df[col].astype(str).isin(str_vals)

    if search:
        term = search.strip().lower()
        if term:
            text_cols = [
                c for c in df.columns
                if not pd.api.types.is_numeric_dtype(df[c])
                and not pd.api.types.is_datetime64_any_dtype(df[c])
            ]
            if text_cols:
                text_mask = pd.Series(False, index=df.index)
                for col in text_cols:
                    text_mask |= df[col].astype(str).str.contains(
                        term, case=False, na=False, regex=False
                    )
                mask &= text_mask

    return df[mask]


def paginate(df: pd.DataFrame, offset: int, limit: int) -> Tuple[pd.DataFrame, int]:
    total = len(df)
    page = df.iloc[offset: offset + limit]
    return page, total
