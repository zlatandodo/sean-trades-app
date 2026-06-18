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


# Default weights for the composite Relative Strength score (sum = 1.0).
# Now includes the 1-day term. Single source of truth.
WEIGHTS = {"1d": 0.10, "1w": 0.35, "1m": 0.35, "3m": 0.20}


def _ranked_sectors(weights: dict = None) -> list[dict]:
    """
    Fetch all sectors and rank them by the composite Relative Strength score:

        score = perf_1d*w1d + perf_1w*w1w + perf_1m*w1m + perf_3m*w3m

    weights: dict with keys '1d','1w','1m','3m'. Missing keys default to 0.
    Returns the full list sorted by score descending; each item has
    {sector, perf_1d, perf_1w, perf_1m, perf_3m, score}.
    """
    w = {**WEIGHTS, **(weights or {})}

    try:
        perf = Performance()
        df = perf.screener_view(group="Sector")
    except Exception as e:
        print(f"[ERROR] Finviz sector fetch failed: {e}", file=sys.stderr)
        return []

    if df is None or df.empty:
        return []

    _normalize_perf_columns(df)

    z = pd.Series(0, index=df.index)
    df["score"] = (
        df.get("Change", z).fillna(0) * w.get("1d", 0) +
        df.get("Perf Week", z).fillna(0) * w.get("1w", 0) +
        df.get("Perf Month", z).fillna(0) * w.get("1m", 0) +
        df.get("Perf Quart", z).fillna(0) * w.get("3m", 0)
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


def get_top_sectors(top_n: int = 3, weights: dict = None) -> list[dict]:
    """Top N sectors by composite Relative Strength score (see _ranked_sectors)."""
    return _ranked_sectors(weights)[:top_n]


def get_all_sectors_ranked(weights: dict = None) -> list[dict]:
    """All sectors ranked by composite Relative Strength score (see _ranked_sectors)."""
    return _ranked_sectors(weights)


if __name__ == "__main__":
    print("Tutti i settori ordinati per Relative Strength score:\n")
    for s in get_all_sectors_ranked():
        print(f"  {s['score']:+.3f}  {s['sector']:24}  "
              f"1d={s['perf_1d']:+.2%}  1w={s['perf_1w']:+.2%}  "
              f"1m={s['perf_1m']:+.2%}  3m={s['perf_3m']:+.2%}")
