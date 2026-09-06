"""
Fetch real Wall Street data for the ICFINANCE daily posts.

Open post  -> the indices themselves (^GSPC, ^IXIC, ^DJI), read at 16:40 IL -
               10 minutes after the 16:30 IL / 9:30 ET open, so every index has
              already printed a real trade (right at 9:30:00 ET, yfinance often
              has no fresh cash-index price yet). We do NOT post about futures
              contracts - only about the actual market/indices themselves.
Close post -> the same indices after the 23:00 IL close, plus the day's biggest
              S&P 500 mover.

Everything here is real, live data pulled via yfinance - nothing is invented.
If a fetch fails, we raise rather than silently posting a guess, since accuracy
on financial numbers is a hard requirement for this account.
"""
import datetime
import yfinance as yf

OPEN_SYMBOLS = [("^GSPC", "S&P 500"), ("^IXIC", "NASDAQ"), ("^DJI", "DOW")]
CLOSE_SYMBOLS = [("^GSPC", "S&P 500"), ("^IXIC", "NASDAQ"), ("^DJI", "DOW")]

# A small, liquid slice of the S&P 500 used to find a "top mover" for the close
# post without needing a paid full-market-scan API. Not exhaustive by design.
MOVER_WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "JPM", "V",
]


def _pct_change(ticker: yf.Ticker) -> float:
    hist = ticker.history(period="2d", interval="1d")
    if len(hist) < 2:
        # market-hours fallback: use fast_info if only one day of history is back yet
        info = ticker.fast_info
        prev = info.get("previousClose") or info.get("regularMarketPreviousClose")
        last = info.get("lastPrice") or info.get("regularMarketPrice")
        if not prev or not last:
            raise RuntimeError(f"insufficient data for {ticker.ticker}")
        return (last - prev) / prev * 100.0
    prev_close = hist["Close"].iloc[-2]
    last_close = hist["Close"].iloc[-1]
    return (last_close - prev_close) / prev_close * 100.0


def _headline(session: str, primary_pct: float) -> str:
    up = primary_pct >= 0
    if session == "open":
        return "Wall Street Opens Higher" if up else "Wall Street Opens Lower"
    return "S&P 500 Closes Higher on the Day" if up else "S&P 500 Closes Lower on the Day"


def _top_mover():
    best = None
    for sym in MOVER_WATCHLIST:
        try:
            pct = _pct_change(yf.Ticker(sym))
        except Exception:
            continue
        if best is None or abs(pct) > abs(best[1]):
            best = (sym, pct)
    if best is None:
        return None
    return {"symbol": best[0], "pct": best[1]}


def get_data(session: str) -> dict:
    symbols = OPEN_SYMBOLS if session == "open" else CLOSE_SYMBOLS
    stats = []
    for sym, name in symbols:
        pct = _pct_change(yf.Ticker(sym))
        stats.append({"label": name, "name": name, "pct": pct})

    primary_pct = stats[0]["pct"]
    now = datetime.datetime.now()

    data = {
        "session_time": "4:40 PM IL" if session == "open" else "11:00 PM IL",
        "headline": _headline(session, primary_pct),
        "stats": stats,
        "date_str": now.strftime("%a · %b %-d").upper() if hasattr(now, "strftime") else str(now),
    }
    if session == "close":
        data["top_mover"] = _top_mover()
    return data
