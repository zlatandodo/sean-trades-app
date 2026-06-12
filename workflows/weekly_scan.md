# Weekly Sean Trades Scanner — SOP

## Objective
Identify the top swing trading setups for the week following the "Back to Basics" method by Sean Trades (@SRxTrades). Run every Sunday evening (or Monday pre-market) so setups are ready before the weekly open.

## Source Material
- EP1: Sector/theme analysis + price action + EMA trend
- EP2: Volume pattern (high move → quiet consolidation → high breakout)
- EP3: Discipline/risk management (not automated — human judgment required)
- X: @SRxTrades posts additional setups and context during the week

## The Method (Checklist)

### 1. Market Context
- SPY and QQQ must both be above their 21 EMA
- If market is bearish/neutral → reduce position size, avoid new longs
- Script checks this automatically → printed in report header

### 2. Sector Identification (Finviz)
- Use `finvizfinance` to pull sector performance (1-week, 1-month, 1-quarter)
- Composite score = 1w×40% + 1m×35% + 3m×25%
- Focus on top 2-3 sectors — these are where "the money is rotating"
- Look for innovation themes: AI, aerospace, semiconductors, biotech, quantum

### 3. Industry Drill-Down (3-Level Funnel)
Replicates Sean's TradingView flow: **Sector → Industry → Leaders**.
- Within each top sector, rank the ~144 Finviz industries by the SAME composite score
- Keep only stocks in the top 3 industries per sector (`TOP_INDUSTRIES_PER_SECTOR`)
- Example: Financial → Banks-Regional, Capital Markets, Asset Management
- This isolates the *sub-sector* leading the move (e.g. Semiconductors within Tech)
- Config: `tools/scanner_sean_trades.py` → `TOP_INDUSTRIES_PER_SECTOR`, `MAX_PER_INDUSTRY`

### 4. Stock Screening (Finviz Filters)
- Market Cap > $2B (no micro-caps)
- Price > $3
- Avg Volume > 500K (enough liquidity)
- Relative Volume > 1 (unusual activity)
- USA stocks only

### 4. Technical Scoring (16-point system)
| Category | Max Score | What to Look For |
|---|---|---|
| Market Trend | 2 | SPY+QQQ above EMA21 |
| EMA Stack | 3 | Price > EMA8 > EMA21 > EMA50 |
| Compression | 3 | Tight base, ATR5 < ATR20 |
| Volume Pattern | 4 | High vol up → Low vol consolidation → High vol breakout |
| Candlestick | 2 | Hammer / Bullish Engulfing / Doji breakout |
| Breakout Proximity | 2 | Within 2% of breakout level |

### 5. Grade Thresholds
| Grade | Score | Action |
|---|---|---|
| A+ | 13.6-16 | Strong setup — full size |
| A | 11.2-13.5 | Good setup — normal size |
| B | 8.8-11.1 | Watchlist — wait for confirmation |
| C | 6.4-8.7 | Skip |
| F | <6.4 | Skip |

### 6. Manual Confirmation (Required Before Trading)
After the scanner runs, manually confirm on TradingView:
1. Is the base on the **daily** timeframe? (weeks of compression = better)
2. Is the volume pattern correct? (high → low → high)
3. Any hammer/engulfing candle at the EMA or support?
4. Is the stock in a **sector narrative** (AI, aerospace, etc.)?
5. Is there a **weekly setup** that aligns with the daily?

**NEVER buy the extension.** Wait for compression → then breakout.

## Running the Scanner

```bash
python3 tools/scanner_sean_trades.py
```

Output: `.tmp/scan_results_YYYYMMDD.csv`

### Scheduled Run (Weekly)
The scanner is scheduled to run automatically via cron every Sunday at 18:00.
See `tools/run_weekly_scan.sh` for the cron setup.

## Output Interpretation
- **`accumulation_breakout`**: Best volume pattern — buy the break
- **`accumulation_setup`**: Volume setting up — add to watchlist
- **`quiet_consolidation`**: Potentially compressing — watch for volume pickup
- **`distribution`**: Avoid — institutions are selling
- **`⚡ NEAR BO`**: Within 2% of breakout — highest priority watchlist

## Edge Cases & Lessons Learned

### Finviz Rate Limiting
- `finvizfinance` library handles JS rendering — no manual scraping needed
- If library fails, scanner falls back to curated 60-stock universe
- Do NOT re-run more than 3x per hour to avoid blocks

### Yahoo Finance Data Lag
- `yfinance` has 15-min delayed data on free tier
- For intraday breakout entries, check TradingView for real-time confirmation
- All EMAs/patterns calculated on daily close (most important per Sean)

### Market Context Override
- If SPY/QQQ are below EMA: scanner still runs but prints a warning
- In this case: only trade A+ setups and reduce size

### Yahoo Finance MultiIndex Columns
- `yf.download()` returns MultiIndex columns when multiple tickers → flatten with `[col[0] for col in df.columns]`
- Already handled in `technical_analysis.py`

### Sector/Industry in results
- Sector + Industry are captured for free during Finviz screening (no extra API calls)
- Cached in `stock_screener.TICKER_INFO` map, attached to each `SetupScore`
- CSV columns: `Sector`, `Industry`; console report groups setups by sector

### Result variability between runs
- Relative volume and prices update in real time during market hours
- Running the scanner twice in one day can give slightly different grades/picks
- For consistency, the scheduled Sunday run uses end-of-week closing data

## Future Improvements
- [ ] Add weekly chart analysis (zoom out first, then daily)
- [ ] Add Fibonacci levels for price targets
- [ ] Integrate TradingView webhook alerts for real-time breakout detection
- [ ] Add sector ETF performance (XLK, SMH, XLY, etc.) for more granular sector analysis
- [ ] Add EP3 risk management rules: position sizing, stop loss calculator
