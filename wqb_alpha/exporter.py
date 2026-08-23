from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import OUTPUT_DIR


def results_dataframe(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if not df.empty and "sharpe" in df.columns:
        df = df.sort_values("sharpe", ascending=False, na_position="last")
    return df


def save_results(rows: list[dict], filename: str = "alphas_sorted_by_sharpe.csv") -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = (OUTPUT_DIR / filename).resolve()
    results_dataframe(rows).to_csv(path, index=False)
    return path
