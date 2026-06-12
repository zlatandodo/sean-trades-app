"""
Fetch industry (sub-sector) performance from Finviz.
Used for the 3-level funnel: Sector -> Industry -> Leaders (Sean Trades method).
"""

import pandas as pd
import json
import sys
from finvizfinance.group.performance import Performance


def get_industry_scores() -> dict[str, float]:
    """
    Return a map {industry_name: composite_score} for all ~144 Finviz industries.
    Composite = 1week(40%) + 1month(35%) + 1quarter(25%), same weighting as sectors.
    """
    try:
        perf = Performance()
        df = perf.screener_view(group="Industry")
    except Exception as e:
        print(f"[ERROR] Finviz industry fetch failed: {e}", file=sys.stderr)
        return {}

    if df is None or df.empty:
        return {}

    # Parse percentage / numeric columns
    for col in ["Perf Week", "Perf Month", "Perf Quart"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace("%", "").str.strip()
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["score"] = (
        df.get("Perf Week", pd.Series(0, index=df.index)).fillna(0) * 0.40 +
        df.get("Perf Month", pd.Series(0, index=df.index)).fillna(0) * 0.35 +
        df.get("Perf Quart", pd.Series(0, index=df.index)).fillna(0) * 0.25
    )

    return {row["Name"]: round(float(row["score"]), 4) for _, row in df.iterrows()}


def rank_industries_in_sector(industries_present: list[str],
                              industry_scores: dict[str, float],
                              top_n: int = 3) -> list[dict]:
    """
    Given the industries present in a sector and the global industry score map,
    return the top N industries by composite score.
    """
    scored = []
    for ind in set(industries_present):
        score = industry_scores.get(ind)
        if score is not None:
            scored.append({"industry": ind, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


if __name__ == "__main__":
    scores = get_industry_scores()
    top = sorted(scores.items(), key=lambda x: -x[1])[:20]
    print("Top 20 industries by composite momentum score:")
    for name, s in top:
        print(f"  {s:+.3f}  {name}")
