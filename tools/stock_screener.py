"""
Screen stocks from Finviz using Sean Trades criteria:
- Market cap > $2B
- Price > $3
- Avg Volume > 500K
- Relative Volume > 1
Uses finvizfinance library to bypass JS rendering.
"""

import pandas as pd
import sys
from finvizfinance.screener.overview import Overview
from finvizfinance.screener.performance import Performance as PerfScreener


SEAN_FILTERS = {
    "Market Cap.": "+Mid (over $2bln)",
    "Price": "Over $3",
    "Average Volume": "Over 500K",
    "Relative Volume": "Over 1",
    "Country": "USA",
}

# Valid Finviz dropdown options for the adjustable Level-1 filters.
# (exact labels accepted by finvizfinance)
FILTER_OPTIONS = {
    "Market Cap.": [
        "+Small (over $300mln)", "+Mid (over $2bln)",
        "+Large (over $10bln)", "+Mega (over $200bln)",
    ],
    "Price": ["Over $1", "Over $2", "Over $3", "Over $5", "Over $10", "Over $20"],
    "Average Volume": [
        "Over 100K", "Over 200K", "Over 500K", "Over 750K", "Over 1M", "Over 2M",
    ],
    "Relative Volume": ["Over 0.5", "Over 0.75", "Over 1", "Over 1.5", "Over 2"],
}


def build_filters(market_cap: str = None, price: str = None,
                  avg_volume: str = None, rel_volume: str = None) -> dict:
    """Build a Finviz filter dict from chosen options, falling back to defaults."""
    return {
        "Market Cap.": market_cap or SEAN_FILTERS["Market Cap."],
        "Price": price or SEAN_FILTERS["Price"],
        "Average Volume": avg_volume or SEAN_FILTERS["Average Volume"],
        "Relative Volume": rel_volume or SEAN_FILTERS["Relative Volume"],
        "Country": "USA",
    }

LEADING_SECTOR_FILTERS = {
    "Technology": {**SEAN_FILTERS, "Sector": "Technology"},
    "Healthcare": {**SEAN_FILTERS, "Sector": "Healthcare"},
    "Financial": {**SEAN_FILTERS, "Sector": "Financial"},
    "Consumer Cyclical": {**SEAN_FILTERS, "Sector": "Consumer Cyclical"},
    "Communication Services": {**SEAN_FILTERS, "Sector": "Communication Services"},
    "Industrials": {**SEAN_FILTERS, "Sector": "Industrials"},
    "Basic Materials": {**SEAN_FILTERS, "Sector": "Basic Materials"},
    "Energy": {**SEAN_FILTERS, "Sector": "Energy"},
}


def fetch_screener(filters: dict = None, order_by: str = "Relative Volume") -> pd.DataFrame:
    """
    Fetch stocks from Finviz screener with given filters.
    Returns DataFrame with ticker, price, volume, sector, industry.
    """
    try:
        screener = Overview()
        screener.set_filter(filters_dict=filters or SEAN_FILTERS)
        df = screener.screener_view(order=order_by, ascend=False, verbose=0)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        print(f"[ERROR] Screener fetch failed: {e}", file=sys.stderr)
        return pd.DataFrame()


# Module-level map: ticker -> {"sector": str, "industry": str}
# Populated as a side effect of the screener functions so the scanner
# can attach sector/industry to each result without extra Finviz calls.
TICKER_INFO: dict[str, dict] = {}


def _record_info(df: pd.DataFrame):
    """Cache sector/industry for each ticker in the dataframe."""
    if df.empty or "Ticker" not in df.columns:
        return
    for _, row in df.iterrows():
        t = row.get("Ticker")
        if t:
            TICKER_INFO[t] = {
                "sector": row.get("Sector", "Unknown"),
                "industry": row.get("Industry", ""),
            }


def get_ticker_info(ticker: str) -> dict:
    """Return cached {'sector','industry'} for a ticker, or Unknown."""
    return TICKER_INFO.get(ticker, {"sector": "Unknown", "industry": ""})


def get_tickers_from_leading_sectors(top_sectors: list[str], max_per_sector: int = 50,
                                     base_filters: dict = None) -> list[str]:
    """
    For each leading sector, fetch top stocks by relative volume.
    Returns deduplicated list of tickers. Caches sector/industry in TICKER_INFO.
    base_filters: optional Finviz filter dict (from build_filters); defaults to SEAN_FILTERS.
    """
    base = base_filters or SEAN_FILTERS
    all_tickers = []
    seen = set()

    for sector_name in top_sectors:
        filters = {**base, "Sector": sector_name}
        df = fetch_screener(filters=filters)
        if df.empty:
            continue

        _record_info(df)
        tickers = df["Ticker"].dropna().tolist()[:max_per_sector]
        for t in tickers:
            if t not in seen:
                seen.add(t)
                all_tickers.append(t)

    return all_tickers


def get_all_candidate_tickers(max_tickers: int = 200) -> list[str]:
    """
    Run Finviz screener with Sean Trades base criteria (no sector filter).
    Returns list of tickers sorted by relative volume. Caches sector/industry.
    """
    df = fetch_screener()
    if df.empty:
        return []

    _record_info(df)
    tickers = df["Ticker"].dropna().tolist()
    return tickers[:max_tickers]


def get_tickers_3level_funnel(top_sectors: list[str],
                              industry_scores: dict[str, float],
                              top_industries_per_sector: int = 3,
                              max_per_industry: int = 25) -> tuple[list[str], list[dict]]:
    """
    Sean Trades 3-level funnel: Sector -> Industry -> Leaders.

    For each top sector:
      1. Fetch all stocks matching base criteria in that sector (with Industry labels)
      2. Rank the industries present by composite momentum score
      3. Keep only stocks in the top N industries of that sector

    Args:
        top_sectors: list of leading sector names (from finviz_sectors)
        industry_scores: {industry_name: score} from finviz_industries
        top_industries_per_sector: how many leading industries to keep per sector
        max_per_industry: cap stocks per industry

    Returns:
        (tickers, funnel_detail) where funnel_detail describes the chosen
        sector -> industry breakdown for the report.
    """
    from tools.finviz_industries import rank_industries_in_sector

    all_tickers = []
    seen = set()
    funnel_detail = []

    for sector_name in top_sectors:
        filters = {**SEAN_FILTERS, "Sector": sector_name}
        df = fetch_screener(filters=filters)
        if df.empty or "Industry" not in df.columns:
            continue

        _record_info(df)

        # Rank industries present in this sector
        industries_present = df["Industry"].dropna().tolist()
        top_inds = rank_industries_in_sector(
            industries_present, industry_scores, top_n=top_industries_per_sector
        )
        top_ind_names = {ti["industry"] for ti in top_inds}

        # Keep only stocks in the leading industries
        sector_tickers = []
        for ind_name in top_ind_names:
            ind_df = df[df["Industry"] == ind_name]
            ind_tickers = ind_df["Ticker"].dropna().tolist()[:max_per_industry]
            for t in ind_tickers:
                if t not in seen:
                    seen.add(t)
                    all_tickers.append(t)
                    sector_tickers.append(t)

        funnel_detail.append({
            "sector": sector_name,
            "top_industries": top_inds,
            "n_tickers": len(sector_tickers),
        })

    return all_tickers, funnel_detail


if __name__ == "__main__":
    df = fetch_screener()
    if not df.empty:
        print(f"Found {len(df)} stocks")
        print(df[["Ticker", "Sector", "Industry", "Price", "Change", "Volume"]].head(20).to_string())
    else:
        print("No stocks found")
        sys.exit(1)
