from datetime import date, datetime, timedelta

import yfinance as yf


def fetch(ticker, days=365):
    """Fetch daily price history. Returns a DataFrame or empty DataFrame."""
    end = datetime.today() + timedelta(days=1)
    start = end - timedelta(days=days)
    data = yf.download(ticker, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
    return data


def fetch_and_save(ticker, days=365):
    """Fetch and save to CSV. Returns the filename."""
    data = fetch(ticker, days)
    if data.empty:
        return None
    filename = f"{ticker.lower()}_prices.csv"
    data.to_csv(filename)
    return filename


def compute_ema50_rsi(close):
    """Compute EMA50 and RSI(14) series for a close price Series."""
    ema50 = close.ewm(span=50, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1 / 14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - 100 / (1 + rs)
    return ema50, rsi


def fetch_earnings_info(ticker):
    """Fetch next earnings date + estimates. Returns a dict."""
    info = {"ticker": ticker, "earnings_date": "N/A", "days_away": "—",
            "eps_est": "N/A", "rev_est": "N/A", "high_52w": "N/A"}
    try:
        t = yf.Ticker(ticker)
        cal = t.calendar
        stock_info = t.info

        # Earnings date
        dates = cal.get("Earnings Date", [])
        if dates:
            next_date = dates[0]
            info["earnings_date"] = next_date.strftime("%Y-%m-%d") if hasattr(next_date, "strftime") else str(next_date)
            today = date.today()
            if hasattr(next_date, "strftime"):
                delta = (next_date - today).days
                info["days_away"] = f"{delta}d" if delta >= 0 else f"{abs(delta)}d ago"

        # EPS estimate
        eps = cal.get("Earnings Average")
        if eps is not None:
            info["eps_est"] = f"${eps:.2f}"

        # Revenue estimate
        rev = cal.get("Revenue Average")
        if rev is not None:
            if rev >= 1e9:
                info["rev_est"] = f"${rev/1e9:.1f}B"
            elif rev >= 1e6:
                info["rev_est"] = f"${rev/1e6:.1f}M"
            else:
                info["rev_est"] = f"${rev:,.0f}"

        # 52-week high
        high = stock_info.get("fiftyTwoWeekHigh")
        if high is not None:
            info["high_52w"] = f"${high:.2f}"

    except Exception as e:
        print(f"Error fetching earnings for {ticker}: {e}")

    return info


TICKERS = ["UUUU", "ASPI", "UEC"]

if __name__ == "__main__":
    for ticker in TICKERS:
        print(f"Fetching {ticker}...")
        result = fetch_and_save(ticker)
        if result:
            print(f"  Saved {result}")
        else:
            print(f"  WARNING: No data returned for {ticker}")
