"""
Technical analysis engine for Sean Trades scanner.
Calculates EMAs, volume patterns, candlestick patterns, compression, and scores each setup.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SetupScore:
    ticker: str
    sector: str = "Unknown"
    industry: str = ""
    total_score: float = 0.0
    max_score: float = 16.0
    grade: str = "F"
    signals: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Individual scores
    market_trend_score: float = 0.0     # /2
    ema_trend_score: float = 0.0        # /3 (1 per EMA above price)
    compression_score: float = 0.0      # /3
    volume_pattern_score: float = 0.0   # /4
    candlestick_score: float = 0.0      # /2
    breakout_proximity_score: float = 0.0  # /2

    # Raw data
    price: float = 0.0
    ema8: float = 0.0
    ema21: float = 0.0
    ema50: float = 0.0
    rel_volume: float = 0.0
    compression_ratio: float = 0.0
    last_candle_pattern: str = "none"
    near_breakout: bool = False
    volume_pattern: str = "unknown"

    def compute_grade(self):
        pct = self.total_score / self.max_score
        if pct >= 0.85:
            self.grade = "A+"
        elif pct >= 0.70:
            self.grade = "A"
        elif pct >= 0.55:
            self.grade = "B"
        elif pct >= 0.40:
            self.grade = "C"
        else:
            self.grade = "F"


def get_market_trend(spy_df: pd.DataFrame, qqq_df: pd.DataFrame) -> tuple[bool, float]:
    """
    Check if SPY and QQQ are both in uptrend (above 21 EMA).
    Returns (is_bullish, score 0-2).
    """
    score = 0.0
    for df, name in [(spy_df, "SPY"), (qqq_df, "QQQ")]:
        if df is None or df.empty or len(df) < 21:
            continue
        closes = df["Close"]
        ema21 = closes.ewm(span=21, adjust=False).mean()
        if closes.iloc[-1] > ema21.iloc[-1]:
            score += 1.0
    return score >= 1.0, score


def compute_emas(closes: pd.Series) -> tuple[float, float, float]:
    """Return (ema8, ema21, ema50) for latest close."""
    if len(closes) < 50:
        return 0.0, 0.0, 0.0
    e8 = closes.ewm(span=8, adjust=False).mean().iloc[-1]
    e21 = closes.ewm(span=21, adjust=False).mean().iloc[-1]
    e50 = closes.ewm(span=50, adjust=False).mean().iloc[-1]
    return round(e8, 4), round(e21, 4), round(e50, 4)


def score_ema_trend(price: float, ema8: float, ema21: float, ema50: float) -> tuple[float, list[str]]:
    """
    Score: +1 per EMA that price is above (max 3).
    Ideal: price > EMA8 > EMA21 > EMA50 (stacked bullish trend).
    """
    score = 0.0
    signals = []
    if price > ema8:
        score += 1.0
        signals.append("Above EMA8")
    if price > ema21:
        score += 1.0
        signals.append("Above EMA21")
    if price > ema50:
        score += 1.0
        signals.append("Above EMA50")
    return score, signals


def score_compression(df: pd.DataFrame) -> tuple[float, float, list[str]]:
    """
    Compression = tight consolidation.
    Sean Trades: the tighter the base, the better the upcoming move.

    Method:
    - ATR(5) / ATR(20): if recent range is much smaller than historical → compressed
    - Also check if the stock is in a narrow high-low band in last 10 days

    Returns (score 0-3, compression_ratio, signals)
    """
    if len(df) < 25:
        return 0.0, 0.0, ["Insufficient data"]

    highs = df["High"]
    lows = df["Low"]
    closes = df["Close"]

    # True Range for last 20 days
    tr_list = []
    for i in range(1, len(df)):
        h = highs.iloc[i]
        l = lows.iloc[i]
        c_prev = closes.iloc[i - 1]
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        tr_list.append(tr)

    tr_series = pd.Series(tr_list)
    atr5 = tr_series.iloc[-5:].mean() if len(tr_series) >= 5 else tr_series.mean()
    atr20 = tr_series.iloc[-20:].mean() if len(tr_series) >= 20 else tr_series.mean()

    compression_ratio = atr5 / atr20 if atr20 > 0 else 1.0

    # Range compression in last 10 days
    recent_high = highs.iloc[-10:].max()
    recent_low = lows.iloc[-10:].min()
    price = closes.iloc[-1]
    range_pct = (recent_high - recent_low) / price if price > 0 else 1.0

    signals = []
    score = 0.0

    # ATR compression score
    if compression_ratio < 0.50:
        score += 1.5
        signals.append(f"Strong ATR compression ({compression_ratio:.2f}x)")
    elif compression_ratio < 0.70:
        score += 1.0
        signals.append(f"Moderate ATR compression ({compression_ratio:.2f}x)")
    elif compression_ratio < 0.85:
        score += 0.5
        signals.append(f"Mild ATR compression ({compression_ratio:.2f}x)")

    # Range tightness score
    if range_pct < 0.05:
        score += 1.5
        signals.append(f"Very tight 10-day range ({range_pct:.1%})")
    elif range_pct < 0.08:
        score += 1.0
        signals.append(f"Tight 10-day range ({range_pct:.1%})")
    elif range_pct < 0.12:
        score += 0.5
        signals.append(f"Moderate 10-day range ({range_pct:.1%})")

    return min(score, 3.0), round(compression_ratio, 3), signals


def score_volume_pattern(df: pd.DataFrame) -> tuple[float, str, list[str]]:
    """
    Sean Trades volume pattern (EP2):
    STRONG pattern: High vol on move up → Low vol on consolidation → High vol on breakout

    Score:
    - Initial move was on high volume (+1)
    - Consolidation (last 10 days) is on declining/low volume (+1.5)
    - Recent volume spike (last 3 days) or above-average volume (+1.5)

    Returns (score 0-4, pattern_name, signals)
    """
    if len(df) < 30:
        return 0.0, "insufficient_data", []

    volumes = df["Volume"]
    closes = df["Close"]

    avg_vol_20 = volumes.iloc[-20:].mean()
    avg_vol_30 = volumes.iloc[-30:].mean()

    # Look back for the initial big move (last 20-40 days)
    lookback = min(40, len(df) - 10)
    move_window = volumes.iloc[-lookback:-10]
    consolidation_window = volumes.iloc[-10:-3]
    recent_window = volumes.iloc[-3:]

    avg_move = move_window.mean() if len(move_window) > 0 else avg_vol_30
    avg_consol = consolidation_window.mean() if len(consolidation_window) > 0 else avg_vol_30
    avg_recent = recent_window.mean() if len(recent_window) > 0 else avg_vol_30

    signals = []
    score = 0.0
    pattern = "unknown"

    # Check initial move had high volume
    initial_high_vol = avg_move > avg_vol_30 * 1.1
    if initial_high_vol:
        score += 1.0
        signals.append("Initial move had above-avg volume")

    # Check consolidation is quiet (low volume)
    consolidation_quiet = avg_consol < avg_vol_30 * 0.85
    if consolidation_quiet:
        score += 1.5
        signals.append(f"Quiet consolidation (vol {avg_consol/avg_vol_30:.1%} of avg)")

    # Check recent volume pickup (potential breakout signal)
    recent_spike = avg_recent > avg_vol_30 * 1.2
    recent_above_avg = avg_recent > avg_vol_30
    if recent_spike:
        score += 1.5
        signals.append(f"Recent volume spike ({avg_recent/avg_vol_30:.1%} of avg)")
    elif recent_above_avg:
        score += 0.75
        signals.append(f"Recent volume above avg ({avg_recent/avg_vol_30:.1%})")

    # Determine pattern name
    if initial_high_vol and consolidation_quiet and recent_spike:
        pattern = "accumulation_breakout"
    elif initial_high_vol and consolidation_quiet:
        pattern = "accumulation_setup"
    elif consolidation_quiet:
        pattern = "quiet_consolidation"
    elif not consolidation_quiet and avg_consol > avg_vol_30 * 1.2:
        pattern = "distribution"
        signals.append("WARNING: High vol during consolidation (distribution?)")
        score = max(0, score - 1.0)
    else:
        pattern = "neutral"

    return min(score, 4.0), pattern, signals


def score_candlesticks(df: pd.DataFrame) -> tuple[float, str, list[str]]:
    """
    Detect key candle patterns Sean Trades uses:
    - Hammer (reversal/retest): +2
    - Bullish Engulfing: +2
    - Doji (indecision, potential breakout): +1
    - Shooting Star (bearish): -1
    - Bearish Engulfing: -1

    Returns (score 0-2, pattern_name, signals)
    """
    if len(df) < 3:
        return 0.0, "none", []

    o = df["Open"].iloc[-1]
    h = df["High"].iloc[-1]
    l = df["Low"].iloc[-1]
    c = df["Close"].iloc[-1]

    prev_o = df["Open"].iloc[-2]
    prev_h = df["High"].iloc[-2]
    prev_l = df["Low"].iloc[-2]
    prev_c = df["Close"].iloc[-2]

    body = abs(c - o)
    full_range = h - l if h != l else 0.0001
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    signals = []
    score = 0.0
    pattern = "none"

    # Hammer: small body, long lower wick (>2x body), close in upper half
    if (body < full_range * 0.35 and
            lower_wick >= body * 2.0 and
            upper_wick < body * 0.5 and
            c > (h + l) / 2):
        pattern = "hammer"
        score = 2.0
        signals.append("Hammer candle (bullish reversal signal)")

    # Bullish Engulfing: current green candle body engulfs previous red body
    elif (c > o and  # current is green
          prev_c < prev_o and  # previous is red
          c > prev_o and  # current close > previous open
          o < prev_c):  # current open < previous close
        pattern = "bullish_engulfing"
        score = 2.0
        signals.append("Bullish Engulfing (strong momentum signal)")

    # Doji: tiny body relative to range
    elif body < full_range * 0.10:
        pattern = "doji"
        score = 1.0
        signals.append("Doji candle (indecision - watch for breakout)")

    # Shooting Star: small body, long upper wick, close near lows (bearish)
    elif (body < full_range * 0.35 and
          upper_wick >= body * 2.0 and
          lower_wick < body * 0.5 and
          c < (h + l) / 2):
        pattern = "shooting_star"
        score = 0.0
        signals.append("Shooting Star (bearish - avoid long)")

    # Bearish Engulfing
    elif (c < o and
          prev_c > prev_o and
          c < prev_o and
          o > prev_c):
        pattern = "bearish_engulfing"
        score = 0.0
        signals.append("Bearish Engulfing (bearish - avoid long)")

    # Strong bullish close (closed in top 25% of day's range)
    elif c > l + full_range * 0.75 and c > o:
        pattern = "strong_close"
        score = 1.5
        signals.append("Strong bullish close (top of range)")

    # Weak bearish close (closed in bottom 25%)
    elif c < l + full_range * 0.25 and c < o:
        pattern = "weak_close"
        score = 0.0
        signals.append("Weak bearish close (bottom of range)")

    return min(score, 2.0), pattern, signals


def score_breakout_proximity(df: pd.DataFrame, ema8: float, ema21: float) -> tuple[float, bool, list[str]]:
    """
    Check if stock is near a key breakout level.
    Sean Trades: buy the break of previous day's high / consolidation high.

    Score:
    - Price is within 2% below the 10-day high (near breakout): +1
    - Price is above yesterday's high (breaking out now): +2
    - Stock retesting a key EMA (within 1%): +1
    """
    if len(df) < 11:
        return 0.0, False, []

    price = df["Close"].iloc[-1]
    high_10d = df["High"].iloc[-10:].max()
    yesterday_high = df["High"].iloc[-2]

    signals = []
    score = 0.0
    near_breakout = False

    # Breaking above yesterday's high (entry trigger)
    if price > yesterday_high * 1.001:
        score += 2.0
        near_breakout = True
        signals.append(f"Breaking above prior high (${yesterday_high:.2f})")

    # Within 2% of 10-day high (coiling near resistance)
    elif price >= high_10d * 0.98:
        score += 1.0
        near_breakout = True
        signals.append(f"Within 2% of 10-day high (${high_10d:.2f})")

    # Retesting key EMA
    for ema_val, ema_name in [(ema8, "EMA8"), (ema21, "EMA21")]:
        if ema_val > 0 and abs(price - ema_val) / ema_val < 0.015:
            score += 1.0
            signals.append(f"Retesting {ema_name} (${ema_val:.2f})")
            break

    return min(score, 2.0), near_breakout, signals


def analyze_stock(ticker: str, market_score: float,
                  sector: str = "Unknown", industry: str = "") -> Optional[SetupScore]:
    """
    Full technical analysis for a single ticker.
    Returns SetupScore or None if data is unavailable.
    """
    try:
        data = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
        if data is None or len(data) < 30:
            return None

        # Flatten MultiIndex columns if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]

        closes = data["Close"]
        price = float(closes.iloc[-1])

        if price <= 0:
            return None

        setup = SetupScore(ticker=ticker, price=round(price, 2),
                           sector=sector, industry=industry)

        # 1. Market trend (passed in)
        setup.market_trend_score = min(market_score, 2.0)
        if market_score >= 1.5:
            setup.signals.append("Market in bullish trend (SPY+QQQ above EMA)")
        elif market_score >= 1.0:
            setup.signals.append("Market partially bullish")
        else:
            setup.warnings.append("Market not in clear uptrend")

        # 2. EMA trend
        ema8, ema21, ema50 = compute_emas(closes)
        setup.ema8, setup.ema21, setup.ema50 = ema8, ema21, ema50
        ema_score, ema_signals = score_ema_trend(price, ema8, ema21, ema50)
        setup.ema_trend_score = ema_score
        setup.signals.extend(ema_signals)
        if ema_score < 2:
            setup.warnings.append("Not fully above EMAs")

        # 3. Compression
        comp_score, comp_ratio, comp_signals = score_compression(data)
        setup.compression_score = comp_score
        setup.compression_ratio = comp_ratio
        setup.signals.extend(comp_signals)

        # 4. Volume pattern
        vol_score, vol_pattern, vol_signals = score_volume_pattern(data)
        setup.volume_pattern_score = vol_score
        setup.volume_pattern = vol_pattern
        setup.signals.extend(vol_signals)

        # 5. Candlestick
        candle_score, candle_pattern, candle_signals = score_candlesticks(data)
        setup.candlestick_score = candle_score
        setup.last_candle_pattern = candle_pattern
        setup.signals.extend(candle_signals)

        # 6. Breakout proximity
        bo_score, near_bo, bo_signals = score_breakout_proximity(data, ema8, ema21)
        setup.breakout_proximity_score = bo_score
        setup.near_breakout = near_bo
        setup.signals.extend(bo_signals)

        # Total
        setup.total_score = (
            setup.market_trend_score +
            setup.ema_trend_score +
            setup.compression_score +
            setup.volume_pattern_score +
            setup.candlestick_score +
            setup.breakout_proximity_score
        )
        setup.compute_grade()

        return setup

    except Exception as e:
        return None
