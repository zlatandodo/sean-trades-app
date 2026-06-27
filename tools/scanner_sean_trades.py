"""
Sean Trades Weekly Scanner
--------------------------
Emulates the "Back to Basics" method from Sean Trades (@SRxTrades):

1. Identify leading sectors (Finviz Groups - 1d/1w/1m composite)
2. Screen stocks from those sectors (mktcap >2B, price >$3, avgvol >500K, relvol >1)
3. Apply full technical scoring:
   - Market trend (SPY/QQQ above EMA)
   - EMA stack (8/21/50)
   - Compression (tight base = upcoming expansion)
   - Volume pattern (high move → quiet consolidation → high breakout)
   - Candlestick signals (hammer, engulfing, doji)
   - Breakout proximity
4. Output ranked setups (CSV + console report)

Run manually:
    python3 tools/scanner_sean_trades.py

Output: .tmp/scan_results_YYYYMMDD.csv
"""

import sys
import os
import json
import time
import concurrent.futures
from datetime import datetime
import pandas as pd
import yfinance as yf

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.finviz_sectors import get_top_sectors
from tools.stock_screener import (
    get_all_candidate_tickers, get_tickers_from_leading_sectors, get_ticker_info
)
from tools.technical_analysis import analyze_stock, get_market_trend, SetupScore
from tools.net_utils import with_retries

# ── Config ──────────────────────────────────────────────────────────────────
MIN_GRADE = "B"          # Minimum grade to include in report
MAX_WORKERS = 8          # Parallel analysis threads
MAX_TICKERS = 150        # Max tickers to analyze (perf cap)
MAX_PER_SECTOR = 60      # Cap stocks pulled per leading sector
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tmp")
GRADE_ORDER = {"A+": 0, "A": 1, "B": 2, "C": 3, "F": 4}
MIN_SCORE_THRESHOLD = {"A+": 13.6, "A": 11.2, "B": 8.8, "C": 6.4, "F": 0}
# ────────────────────────────────────────────────────────────────────────────


def get_market_context() -> tuple[bool, float]:
    """Download SPY and QQQ and assess market trend."""
    print("📊 Checking market context (SPY/QQQ)...")
    try:
        spy = with_retries(
            lambda: yf.download("SPY", period="3mo", interval="1d",
                                progress=False, auto_adjust=True),
            label="Yahoo SPY")
        qqq = with_retries(
            lambda: yf.download("QQQ", period="3mo", interval="1d",
                                progress=False, auto_adjust=True),
            label="Yahoo QQQ")
        if spy is None or qqq is None or spy.empty or qqq.empty:
            print("   [WARN] Market data unavailable (rate limited)")
            return True, 1.0

        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = [c[0] for c in spy.columns]
        if isinstance(qqq.columns, pd.MultiIndex):
            qqq.columns = [c[0] for c in qqq.columns]

        is_bull, score = get_market_trend(spy, qqq)
        status = "BULLISH" if is_bull else "BEARISH/NEUTRAL"
        print(f"   Market status: {status} (score: {score}/2)")
        return is_bull, score
    except Exception as e:
        print(f"   [WARN] Market context failed: {e}")
        return True, 1.0


def get_candidate_tickers_from_finviz(top_sectors: list[dict], max_per_sector: int = None,
                                      base_filters: dict = None) -> tuple[list[str], list[dict]]:
    """
    2-level selection (Sean Trades method): Sector -> Leaders.
    Pulls ALL stocks (matching base criteria) from the leading sectors, WITHOUT
    narrowing to top industries — the industry funnel was too restrictive.

    Returns (tickers, sector_detail). Falls back to broad screen / curated
    universe if Finviz returns nothing.
    """
    print("🔍 Selecting candidates from leading sectors...")
    cap = max_per_sector or MAX_PER_SECTOR

    sector_names = [s["sector"] for s in top_sectors if s.get("score", 0) > 0]
    if not sector_names:
        print("   [WARN] No leading sectors - falling back to broad screen")
        return get_all_candidate_tickers(max_tickers=MAX_TICKERS), []

    tickers = get_tickers_from_leading_sectors(sector_names, max_per_sector=cap,
                                               base_filters=base_filters)

    # Build per-sector detail for the report (counts only, no industry funnel)
    sector_detail = []
    for name in sector_names:
        n = sum(1 for t in tickers if get_ticker_info(t)["sector"] == name)
        sector_detail.append({"sector": name, "n_tickers": n})
        print(f"   {name}: {n} stocks")

    # Supplement with broad screen if too thin
    if len(tickers) < 20:
        print(f"   Only {len(tickers)} from sectors - supplementing with broad screen")
        broad = get_all_candidate_tickers(max_tickers=MAX_TICKERS)
        seen = set(tickers)
        for t in broad:
            if t not in seen:
                tickers.append(t)
                seen.add(t)

    if not tickers:
        print("   [WARN] Finviz returned nothing - using fallback universe")
        return get_fallback_universe(), []

    return tickers[:MAX_TICKERS], sector_detail


def get_fallback_universe() -> list[str]:
    """
    Fallback: broad universe of liquid US stocks across sectors.
    These are well-known liquid names that meet Sean's base criteria.
    Used when Finviz scraping is blocked.
    """
    return [
        # Tech / AI / Semis
        "NVDA", "AMD", "AVGO", "TSM", "QCOM", "INTC", "MU", "AMAT", "LRCX", "KLAC",
        "SMCI", "ARM", "MRVL", "ON", "WOLF", "ENPH", "FSLR",
        # Software
        "MSFT", "META", "GOOGL", "CRM", "NOW", "SNOW", "PLTR", "HUBS", "DDOG", "PANW",
        "ZS", "CRWD", "NET", "OKTA", "MNDY", "APP", "RBLX", "U",
        # Consumer / Growth
        "AMZN", "TSLA", "UBER", "LYFT", "ABNB", "DASH", "SHOP", "MELI", "SE", "GRAB",
        # Healthcare / Biotech
        "LLY", "NVO", "REGN", "VRTX", "GILD", "MRNA", "HIMS",
        # Financials
        "JPM", "GS", "MS", "COIN", "HOOD", "SOFI",
        # Aerospace / Defense
        "RTX", "LHX", "NOC", "GD", "RKLB", "LUNR", "ASTS",
        # Energy
        "XOM", "CVX", "FANG", "DVN", "OXY",
        # Quantum / Emerging
        "IONQ", "QUBT", "RGTI", "QMCO",
        # ETFs for sector leaders
        "XLK", "SMH", "SOXX", "XLY", "XLF", "XLE",
    ]


def analyze_batch(tickers: list[str], market_score: float) -> list[SetupScore]:
    """Analyze all tickers in parallel."""
    results = []
    total = len(tickers)
    done = 0

    print(f"\n🔬 Analyzing {total} tickers (parallel, {MAX_WORKERS} workers)...")

    def analyze_one(ticker):
        info = get_ticker_info(ticker)
        return analyze_stock(ticker, market_score,
                             sector=info["sector"], industry=info["industry"])

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(analyze_one, t): t for t in tickers}
        for fut in concurrent.futures.as_completed(futures):
            done += 1
            ticker = futures[fut]
            try:
                result = fut.result()
                if result is not None:
                    results.append(result)
            except Exception:
                pass
            if done % 20 == 0 or done == total:
                print(f"   Progress: {done}/{total} analyzed, {len(results)} valid")

    return results


def filter_and_rank(results: list[SetupScore]) -> list[SetupScore]:
    """Filter by minimum grade and rank by total score."""
    min_score = MIN_SCORE_THRESHOLD.get(MIN_GRADE, 0)
    filtered = [r for r in results if r.total_score >= min_score]
    ranked = sorted(filtered, key=lambda x: x.total_score, reverse=True)
    return ranked


def save_results(results: list[SetupScore], sectors: list[dict], market_bull: bool) -> str:
    """Save results to CSV in .tmp/ folder."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    filepath = os.path.join(OUTPUT_DIR, f"scan_results_{date_str}.csv")

    rows = []
    for r in results:
        rows.append({
            "Ticker": r.ticker,
            "Sector": r.sector,
            "Industry": r.industry,
            "Grade": r.grade,
            "Score": round(r.total_score, 1),
            "MaxScore": r.max_score,
            "Price": r.price,
            "EMA8": r.ema8,
            "EMA21": r.ema21,
            "EMA50": r.ema50,
            "Compression": r.compression_ratio,
            "VolPattern": r.volume_pattern,
            "CandlePattern": r.last_candle_pattern,
            "NearBreakout": r.near_breakout,
            "MarketBull": market_bull,
            "EMAScore": r.ema_trend_score,
            "CompScore": r.compression_score,
            "VolScore": r.volume_pattern_score,
            "CandleScore": r.candlestick_score,
            "BOScore": r.breakout_proximity_score,
            "Signals": " | ".join(r.signals),
            "Warnings": " | ".join(r.warnings),
            "ScanDate": date_str,
        })

    df = pd.DataFrame(rows)
    df.to_csv(filepath, index=False)
    return filepath


def print_report(results: list[SetupScore], sectors: list[dict], market_bull: bool,
                 funnel: list[dict] = None):
    """Print human-readable console report."""
    print("\n" + "=" * 70)
    print("  SEAN TRADES WEEKLY SCANNER - RESULTS")
    print("=" * 70)

    # Market context
    market_str = "✅ BULLISH (SPY/QQQ above EMA)" if market_bull else "⚠️  BEARISH/NEUTRAL"
    print(f"\n📈 Market Context: {market_str}")

    # Candidate pool per sector
    if funnel:
        print(f"\n🔻 Candidates per leading sector:")
        for f in funnel:
            print(f"   {f['sector']}: {f['n_tickers']} stocks")

    # Sectors
    if sectors:
        print(f"\n🏆 Leading Sectors:")
        for i, s in enumerate(sectors[:3], 1):
            print(f"   {i}. {s.get('sector', 'N/A')} — Score: {s.get('score', 0):+.1f}")

    # Top setups
    print(f"\n🎯 Top Setups (min grade: {MIN_GRADE}):\n")
    if not results:
        print("   No setups met the minimum criteria this week.")
        return

    print(f"{'#':<3} {'Ticker':<8} {'Grade':<5} {'Score':<7} {'Price':<8} "
          f"{'Vol Pattern':<22} {'Candle':<20} {'Breakout'}")
    print("-" * 85)

    for i, r in enumerate(results[:20], 1):
        bo_flag = "⚡ NEAR BO" if r.near_breakout else ""
        print(f"{i:<3} {r.ticker:<8} {r.grade:<5} "
              f"{r.total_score:.1f}/{r.max_score:.0f}  "
              f"${r.price:<7.2f} "
              f"{r.volume_pattern:<22} "
              f"{r.last_candle_pattern:<20} "
              f"{bo_flag}")

    # Grouped by sector
    print(f"\n🗂️  Setups by Sector:")
    by_sector = {}
    for r in results:
        by_sector.setdefault(r.sector, []).append(r)
    for sector in sorted(by_sector, key=lambda s: -len(by_sector[s])):
        stocks = sorted(by_sector[sector], key=lambda x: -x.total_score)
        tickers_str = ", ".join(f"{r.ticker}({r.grade})" for r in stocks)
        print(f"   • {sector} [{len(stocks)}]: {tickers_str}")

    # Detailed signals for top 5
    print(f"\n📋 Detailed Analysis - Top 5 Setups:")
    for r in results[:5]:
        print(f"\n{'─'*50}")
        print(f"  {r.ticker} | {r.grade} | ${r.price:.2f} | Score: {r.total_score:.1f}/{r.max_score}")
        print(f"  EMAs: 8={r.ema8:.2f} | 21={r.ema21:.2f} | 50={r.ema50:.2f}")
        print(f"  Compression ratio: {r.compression_ratio:.2f}x")
        print(f"  Volume pattern: {r.volume_pattern}")
        for sig in r.signals:
            print(f"  ✅ {sig}")
        for warn in r.warnings:
            print(f"  ⚠️  {warn}")

    print("\n" + "=" * 70)


def run_scan(min_grade: str = None, weights: dict = None, top_n_sectors: int = 3,
             max_per_sector: int = None, base_filters: dict = None) -> dict:
    """
    Programmatic scan entry point (used by the Streamlit dashboard).
    Returns a structured dict instead of only printing.

    Args:
        min_grade: minimum grade to keep (A+/A/B/C)
        weights: RS score weights dict {'1d','1w','1m','3m'}
        top_n_sectors: how many leading sectors to use
        max_per_sector: cap stocks pulled per sector
        base_filters: Finviz filter dict (from stock_screener.build_filters)

    Returns:
        {
          "market_bull": bool, "market_score": float,
          "sectors": [...], "funnel": [...],
          "results": [SetupScore, ...],   # ranked, filtered
          "all_results": [SetupScore, ...],  # unfiltered
          "csv_path": str,
        }
    """
    global MIN_GRADE
    if min_grade:
        MIN_GRADE = min_grade

    market_bull, market_score = get_market_context()
    sectors = get_top_sectors(top_n=top_n_sectors, weights=weights)
    tickers, funnel = get_candidate_tickers_from_finviz(
        sectors, max_per_sector=max_per_sector, base_filters=base_filters)

    if not tickers:
        # No candidates: almost always a data-source outage (Finviz/Yahoo rate limit)
        return {
            "market_bull": market_bull, "market_score": market_score,
            "sectors": sectors, "funnel": funnel,
            "results": [], "all_results": [], "csv_path": None,
            "data_ok": False,
        }

    all_results = analyze_batch(tickers, market_score)
    ranked = filter_and_rank(all_results)
    csv_path = save_results(ranked, sectors, market_bull)

    return {
        "market_bull": market_bull, "market_score": market_score,
        "sectors": sectors, "funnel": funnel, "data_ok": True,
        "results": ranked, "all_results": all_results, "csv_path": csv_path,
    }


def run():
    """Main scanner entry point."""
    print("\n🚀 SEAN TRADES WEEKLY SCANNER STARTING")
    print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Step 1: Market context
    market_bull, market_score = get_market_context()

    if not market_bull:
        print("\n⚠️  WARNING: Market is NOT in a clear uptrend.")
        print("   Sean Trades method recommends avoiding longs in weak markets.")
        print("   Proceeding with scan but expect fewer quality setups.\n")

    # Step 2: Identify leading sectors
    print("\n📊 Identifying leading sectors (Finviz)...")
    sectors = get_top_sectors(top_n=3)
    if sectors:
        for s in sectors:
            print(f"   ✓ {s.get('sector', 'N/A')} — Composite score: {s.get('score', 0):+.2f}")
    else:
        print("   [WARN] Could not fetch sector data from Finviz")

    # Step 3: Get candidate tickers via 3-level funnel
    tickers, funnel = get_candidate_tickers_from_finviz(sectors)
    if not tickers:
        print("[ERROR] No tickers to analyze. Exiting.")
        sys.exit(1)

    # Step 4: Technical analysis
    results = analyze_batch(tickers, market_score)

    # Step 5: Filter and rank
    ranked = filter_and_rank(results)

    # Step 6: Output
    print_report(ranked, sectors, market_bull, funnel)

    filepath = save_results(ranked, sectors, market_bull)
    print(f"\n💾 Full results saved: {filepath}")
    print(f"   Total setups analyzed: {len(results)}")
    print(f"   Setups meeting grade {MIN_GRADE}+: {len(ranked)}")
    print(f"   Top pick: {ranked[0].ticker if ranked else 'None'}")
    print()


if __name__ == "__main__":
    run()
