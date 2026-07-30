import numpy as np
import yfinance as yf
import argparse
from datetime import date, datetime
from vollib.black_scholes.implied_volatility import implied_volatility


def pick_expiry(expirations, target_days=30):
    today = datetime.now().date()
    best = min(
        expirations,
        key=lambda e: abs((datetime.strptime(e, "%Y-%m-%d").date() - today).days - target_days)
    )
    return best


def get_option_chain(ticker, expiry=None):
    t = yf.Ticker(ticker)
    info = t.info
    spot = info.get("currentPrice") or info.get("regularMarketPrice")
    if spot is None:
        raise ValueError(f"Could not determine current price for {ticker}")

    if expiry is None:
        expirations = t.options
        if not expirations:
            raise ValueError(f"No options available for {ticker}")
        expiry = pick_expiry(expirations)

    chain = t.option_chain(expiry)
    return spot, expiry, chain


def compute_iv_hv_ratio(atm_iv, hist_vol):
    if atm_iv is not None and hist_vol is not None and hist_vol > 0 and not np.isnan(hist_vol):
        return atm_iv / hist_vol
    return None


def find_atm_iv(chain, spot, expiry):
    puts = chain.puts.copy()
    tte = (date.fromisoformat(expiry) - date.today()).days / 365

    valid = puts[(puts["lastPrice"] > 0.05) & (puts["volume"] > 0)].copy()
    if valid.empty:
        raise ValueError("No strikes with valid lastPrice")

    valid["dist"] = abs(valid["strike"] - spot)
    best = valid.loc[valid["dist"].idxmin()]

    iv = implied_volatility(best["lastPrice"], spot, best["strike"], tte, 0, "p")
    return best["strike"], iv


def main():
    parser = argparse.ArgumentParser(description="Fetch ATM implied volatility for watchlist")
    parser.add_argument("tickers", nargs="*", help="Ticker symbols (defaults to watchlist)")
    parser.add_argument("-e", "--expiry", type=str, default=None, help="Option expiry YYYY-MM-DD")
    args = parser.parse_args()

    tickers = args.tickers or ["UUUU", "ASPI", "UEC"]

    print(f"{'Ticker':<8} {'Price':<8} {'Expiry':<12} {'ATM Strike':<12} {'IV':<10}")
    print("-" * 50)

    for ticker in tickers:
        try:
            spot, expiry, chain = get_option_chain(ticker, args.expiry)
            strike, iv = find_atm_iv(chain, spot, expiry)
            iv_str = f"{iv:.1%}" if iv is not None else "N/A"
            print(f"{ticker:<8} ${spot:<6.2f} {expiry:<12} ${strike:<10.2f} {iv_str:<10}")
        except Exception as e:
            print(f"{ticker:<8} ERROR — {e}")


if __name__ == "__main__":
    main()
