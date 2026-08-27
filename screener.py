import sys
import html
from datetime import date

import numpy as np

import fetch_iv
from save_snapshot import save_snapshot
from yf_data import compute_ema50_rsi, fetch, fetch_earnings_info

FLAG_IV_HV_MIN = 1.5
FLAG_EARNINGS_DAYS = 5
FLAG_RSI_MAX = 40
MESSAGE_FILE = "daily_message.txt"


def _num(x):
    """Return x unless it's None or NaN."""
    if x is None:
        return None
    if isinstance(x, float) and np.isnan(x):
        return None
    return x


def load_watchlist(path="watchlist.txt"):
    """Read one ticker per line from the watchlist file."""
    with open(path) as f:
        return [line.strip().upper() for line in f if line.strip()]


def analyze_ticker(ticker):
    """Compute price/ATM IV/realized vol/earnings for one ticker. Returns dict or None.

    Returns None if the ticker has no price history.
    """
    data = fetch(ticker)
    if data.empty:
        print(f"  skip {ticker}: no price data", file=sys.stderr)
        return None

    earnings = fetch_earnings_info(ticker)

    close = data[("Close", ticker)]
    returns = np.log(close / close.shift(1))
    vol = returns.rolling(30).std() * np.sqrt(252)
    hist_vol = vol.iloc[-1]

    ema50, rsi = compute_ema50_rsi(close)

    price = None
    atm_iv = None
    expiry_used = None
    strike = None
    try:
        spot, expiry, chain = fetch_iv.get_option_chain(ticker)
        price = spot
        expiry_used = expiry
        strike, atm_iv = fetch_iv.find_atm_iv(chain, spot, expiry)
    except Exception as e:
        print(f"  warning: no options data for {ticker}: {e}", file=sys.stderr)

    if price is None:
        price = close.iloc[-1]

    return {
        "ticker": ticker,
        "price": price,
        "close": _num(close.iloc[-1]),
        "ema50": _num(ema50.iloc[-1]),
        "rsi": _num(rsi.iloc[-1]),
        "atm_iv": atm_iv,
        "hist_vol": hist_vol,
        "iv_hv_ratio": fetch_iv.compute_iv_hv_ratio(atm_iv, hist_vol),
        "expiry_used": expiry_used,
        "strike": strike,
        "earnings": earnings,
    }


def flag_reasons(entry):
    """Return human-readable reasons a ticker is flagged, or an empty list."""
    reasons = []

    ratio = entry["iv_hv_ratio"]
    if ratio is not None and ratio >= FLAG_IV_HV_MIN:
        reasons.append(f"IV/HV {ratio:.2f}x")

    close = entry.get("close")
    ema50 = entry.get("ema50")
    rsi = entry.get("rsi")
    if (
        close is not None
        and ema50 is not None
        and rsi is not None
        and close < ema50
        and rsi <= FLAG_RSI_MAX
    ):
        reasons.append(f"close<EMA50 (${ema50:.2f}), RSI {rsi:.1f}")

    days = entry["earnings"]["days_away"]
    if days and days.endswith("d") and not days.endswith(" ago"):
        try:
            n = int(days[:-1])
        except ValueError:
            n = None
        if n is not None and 0 <= n <= FLAG_EARNINGS_DAYS:
            reasons.append(f"earnings in {days}")

    return reasons


NAMES = ["Ticker", "Price", "Earnings", "Days", "ATM IV", "IV/HV",
         "HistVol", "52WHigh", "EMA", "RSI"]
WIDTHS = [6, 7, 10, 4, 7, 7, 8, 8, 7, 5]


def _fmt_table(rows):
    """Format rows (tuples of already-formatted strings) as a fixed-width table."""
    header = " ".join(
        f"{name:>{w}}" if i else f"{name:<{w}}"
        for i, (name, w) in enumerate(zip(NAMES, WIDTHS))
    )
    lines = [header]
    for r in rows:
        cells = [
            f"{r[i]:>{WIDTHS[i]}}" if i else f"{r[i]:<{WIDTHS[i]}}"
            for i in range(len(NAMES))
        ]
        lines.append(" ".join(cells))
    return "\n".join(lines)


def format_message(entries):
    """Build the alert (HTML for Telegram): banner + flagged line + full table."""
    entries = sorted(
        entries,
        key=lambda e: (
            not bool(flag_reasons(e)),
            _num(e["iv_hv_ratio"]) is None,
            -(_num(e["iv_hv_ratio"]) or 0),
        ),
    )

    rows = []
    for entry in entries:
        e = entry["earnings"]
        flagged = bool(flag_reasons(entry))
        ticker = entry["ticker"]
        price = f"${entry['price']:.2f}" if _num(entry["price"]) else "\u2014"
        atm_iv = f"{entry['atm_iv']:.1%}" if _num(entry["atm_iv"]) else "\u2014"
        hist_vol = f"{entry['hist_vol']:.1%}" if _num(entry["hist_vol"]) else "\u2014"
        ratio = (
            f"{entry['iv_hv_ratio']:.2f}x"
            if _num(entry["iv_hv_ratio"])
            else "\u2014"
        )
        ema = f"${entry['ema50']:.2f}" if _num(entry.get("ema50")) else "\u2014"
        rsi = f"{entry['rsi']:.1f}" if _num(entry.get("rsi")) else "\u2014"
        row = (
            ticker, price, str(e["earnings_date"]), e["days_away"],
            atm_iv, ratio, hist_vol, e["high_52w"], ema, rsi,
        )
        if flagged:
            row = (f"<b>{ticker:<{WIDTHS[0]}}</b>",) + row[1:]
        rows.append(row)

    table = _fmt_table(rows)

    flagged = [
        f"<b>{entry['ticker']}</b> ({html.escape(reason)})"
        for entry in entries
        for reason in flag_reasons(entry)
    ]
    lines = [f"<b>\U0001f4c8 IV Screener \u2014 {date.today().isoformat()}</b>"]
    if flagged:
        lines = [
            "<b>\U0001f6a8 ACTION ALERT \U0001f6a8</b>",
            "Flagged: " + " \u00b7 ".join(flagged),
            "",
        ] + lines
    return "\n".join(lines + ["<pre>", table, "</pre>"])


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    tickers = sys.argv[1:] or load_watchlist()
    if not tickers:
        print("no tickers in watchlist.txt", file=sys.stderr)
        return 1

    print(f"Scanning {len(tickers)} tickers...")
    entries = []
    snapshot = {}
    for ticker in tickers:
        print(f"  {ticker}...", flush=True)
        entry = analyze_ticker(ticker)
        if entry is None:
            continue
        entries.append(entry)
        snapshot[ticker] = {
            "price": entry["price"],
            "atm_iv": entry["atm_iv"],
            "hist_vol": entry["hist_vol"],
            "iv_hv_ratio": entry["iv_hv_ratio"],
            "expiry_used": entry["expiry_used"],
            "strike": entry["strike"],
        }

    if not entries:
        print("no tickers could be analyzed", file=sys.stderr)
        return 1

    save_snapshot(snapshot)

    message = format_message(entries)
    with open(MESSAGE_FILE, "w", encoding="utf-8") as f:
        f.write(message)
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
