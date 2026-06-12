"""
Fetch sector performance from Finviz using finvizfinance library.
Returns ranked sectors for the Sean Trades scanner.
"""

import pandas as pd
import json
import sys
from finvizfinance.group.performance import Performance


def _normalize_perf_columns(df):
    """
    Finviz returns 'Perf Week' as a percent string ('2.93%') but
    'Perf Month'/'Perf Quart' as decimals (0.0152). Put them all on the
    SAME decimal scale so the weighted composite is consistent.
    """
    # Perf Week: strip % -> numeric -> divide by 100 to match decimal scale
    if "Perf Week" in df.columns:
        s = df["Perf Week"].astype(str).str.replace("%", "").str.strip()
        df["Perf Week"] = pd.to_numeric(s, errors="coerce") / 100.0

    # Perf Month / Quart: already decimals, but coerce defensively
    for col in ["Perf Month", "Perf Quart"]:
        if col in df.columns:
            s = df[col].astype(str).str.replace("%", "").str.strip()
            v = pd.to_numeric(s, errors="coerce")
            # If a value looks like a percent (abs>1.5), rescale to decimal
            df[col] = v.where(v.abs() <= 1.5, v / 100.0)

    if "Change" in df.columns:
        df["Change"] = pd.to_numeric(df["Change"], errors="coerce")


def get_top_sectors(top_n: int = 3) -> list[dict]:
    """
    Score sectors by composite performance: 1week(40%) + 1month(35%) + 1quarter(25%).
    Sean Trades: look for sectors leading over last day, week, and month.
    Returns top N sectors sorted by composite score.
    """
    try:
        perf = Performance()
        df = perf.screener_view(group="Sector")
    except Exception as e:
        print(f"[ERROR] Finviz sector fetch failed: {e}", file=sys.stderr)
        return []

    if df is None or df.empty:
        return []

    _normalize_perf_columns(df)

    # Composite score: week(40%) + month(35%) + quarter(25%)
    df["score"] = (
        df.get("Perf Week", pd.Series(0, index=df.index)).fillna(0) * 0.40 +
        df.get("Perf Month", pd.Series(0, index=df.index)).fillna(0) * 0.35 +
        df.get("Perf Quart", pd.Series(0, index=df.index)).fillna(0) * 0.25
    )

    df_sorted = df.sort_values("score", ascending=False)
    top = df_sorted.head(top_n)

    result = []
    for _, row in top.iterrows():
        result.append({
            "sector": row.get("Name", ""),
            "score": round(float(row["score"]), 4),
            "perf_1w": round(float(row.get("Perf Week", 0) or 0), 4),
            "perf_1m": round(float(row.get("Perf Month", 0) or 0), 4),
            "perf_3m": round(float(row.get("Perf Quart", 0) or 0), 4),
            "perf_1d": round(float(row.get("Change", 0) or 0), 4),
        })

    return result


# Weights used for the composite Relative Strength score (single source of truth)
WEIGHTS = {"1w": 0.40, "1m": 0.35, "3m": 0.25}


def get_all_sectors_ranked() -> list[dict]:
    """
    Return ALL Finviz sectors with the full breakdown used by the
    composite Relative Strength score, sorted by score descending.

    score = perf_1w*0.40 + perf_1m*0.35 + perf_3m*0.25

    Each item: {sector, perf_1d, perf_1w, perf_1m, perf_3m, score}.
    """
    try:
        perf = Performance()
        df = perf.screener_view(group="Sector")
    except Exception as e:
        print(f"[ERROR] Finviz sector fetch failed: {e}", file=sys.stderr)
        return []

    if df is None or df.empty:
        return []

    _normalize_perf_columns(df)

    df["score"] = (
        df.get("Perf Week", pd.Series(0, index=df.index)).fillna(0) * WEIGHTS["1w"] +
        df.get("Perf Month", pd.Series(0, index=df.index)).fillna(0) * WEIGHTS["1m"] +
        df.get("Perf Quart", pd.Series(0, index=df.index)).fillna(0) * WEIGHTS["3m"]
    )

    df_sorted = df.sort_values("score", ascending=False)
    result = []
    for _, row in df_sorted.iterrows():
        result.append({
            "sector": row.get("Name", ""),
            "perf_1d": round(float(row.get("Change", 0) or 0), 4),
            "perf_1w": round(float(row.get("Perf Week", 0) or 0), 4),
            "perf_1m": round(float(row.get("Perf Month", 0) or 0), 4),
            "perf_3m": round(float(row.get("Perf Quart", 0) or 0), 4),
            "score": round(float(row["score"]), 4),
        })
    return result


if __name__ == "__main__":
    print("Tutti i settori ordinati per Relative Strength score:\n")
    for s in get_all_sectors_ranked():
        print(f"  {s['score']:+.3f}  {s['sector']:24}  "
              f"1w={s['perf_1w']:+.2%}  1m={s['perf_1m']:+.2%}  3m={s['perf_3m']:+.2%}")
