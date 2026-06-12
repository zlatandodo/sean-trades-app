"""
Fetch sector performance from Finviz using finvizfinance library.
Returns ranked sectors for the Sean Trades scanner.
"""

import pandas as pd
import json
import sys
from finvizfinance.group.performance import Performance


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

    # Parse percentage columns - they come as strings like '2.93%' or floats
    for col in ["Perf Week", "Perf Month", "Perf Quart"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace("%", "").str.strip()
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Also parse Change (1-day)
    if "Change" in df.columns:
        df["Change"] = pd.to_numeric(df["Change"], errors="coerce")

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


if __name__ == "__main__":
    sectors = get_top_sectors(top_n=5)
    print(json.dumps(sectors, indent=2))
