"""
Network resilience helpers: retry with exponential backoff for the external
data sources (Finviz, Yahoo Finance) that occasionally rate-limit (429/503).
"""

import time
import sys


def with_retries(fn, attempts: int = 4, base_delay: float = 2.0,
                 label: str = "request"):
    """
    Call fn() with exponential backoff on failure.

    Retries on any exception (Finviz 503, yfinance YFRateLimitError, transient
    network errors). Waits base_delay, 2x, 4x... between attempts.

    Returns fn()'s result, or None if all attempts fail (caller decides
    fallback). Never raises — designed so the scanner degrades gracefully.
    """
    delay = base_delay
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last = e
            if i < attempts - 1:
                print(f"[retry] {label} failed ({str(e)[:80]}) — "
                      f"attempt {i + 1}/{attempts}, waiting {delay:.0f}s",
                      file=sys.stderr)
                time.sleep(delay)
                delay *= 2
    print(f"[retry] {label} gave up after {attempts} attempts: "
          f"{str(last)[:120]}", file=sys.stderr)
    return None


def is_rate_limit_error(exc: Exception) -> bool:
    """Heuristic: does this exception look like a rate-limit / throttling error?"""
    msg = str(exc).lower()
    return any(k in msg for k in ("rate limit", "429", "503", "too many requests",
                                  "service unavailable"))
