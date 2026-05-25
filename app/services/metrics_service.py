from typing import Dict, List

import pandas as pd


def get_metrics(df: pd.DataFrame) -> Dict:
    numeric_cols: List[str] = list(df.select_dtypes(include="number").columns)
    datetime_cols: List[str] = list(df.select_dtypes(include="datetime").columns)
    # Remaining object/category columns treated as categorical
    categorical_cols: List[str] = [
        c for c in df.select_dtypes(include=["object", "category"]).columns
    ]

    null_summary: Dict[str, float] = {
        col: round(df[col].isna().sum() / max(len(df), 1) * 100, 2)
        for col in df.columns
    }

    return {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "null_summary": null_summary,
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "datetime_columns": datetime_cols,
    }
