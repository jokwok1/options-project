import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys


def load_price_csv(csv_file, ticker):
    """Load a price CSV. Returns a DataFrame."""
    df = pd.read_csv(csv_file, header=[0, 1], index_col=0)
    df.index.name = "Date"
    df.index = pd.to_datetime(df.index)
    return df


def add_realized_vol(df, ticker, window=30):
    """Add 30-day annualized realized vol column. Returns the DataFrame."""
    close = df[("Close", ticker)]
    returns = np.log(close / close.shift(1))
    df[("RealizedVol", ticker)] = returns.rolling(window).std() * np.sqrt(252)
    return df


def plot_two_panel(df, ticker, out_png):
    """Plot price + realized vol on two panels (shared x-axis). Saves to PNG."""
    close = df[("Close", ticker)]
    vol = df[("RealizedVol", ticker)]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True,
                                     gridspec_kw={"height_ratios": [3, 1]})

    ax1.plot(close.index, close.values, linewidth=1.2)
    ax1.set_ylabel("Price ($)")
    ax1.set_title(f"{ticker} — Daily Close & 30-Day Realized Volatility")
    ax1.grid(True, alpha=0.3)

    ax2.plot(vol.index, vol.values, linewidth=1.2, color="tab:orange")
    ax2.set_ylabel("Realized Vol")
    ax2.set_xlabel("Date")
    ax2.grid(True, alpha=0.3)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))

    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    print(f"Saved {out_png}")


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "UUUU"
    csv_file = f"{ticker.lower()}_prices.csv"
    out_png = f"{ticker.lower()}_vol.png"

    df = load_price_csv(csv_file, ticker)
    df = add_realized_vol(df, ticker)

    # Save updated CSV
    df.to_csv(csv_file)
    print(f"Updated {csv_file} with RealizedVol column")

    # Plot
    plot_two_panel(df, ticker, out_png)

    # Show tail
    close = df[("Close", ticker)]
    vol = df[("RealizedVol", ticker)]
    tail = pd.DataFrame({"Close": close, "RealizedVol": vol}).tail(10)
    print("\nTail (last 10 rows):")
    print(tail.to_string())
