import pandas as pd
import matplotlib.pyplot as plt
import sys


def load_csv(csv_file, ticker):
    """Load a price CSV. Returns a Series of closing prices."""
    df = pd.read_csv(csv_file, header=[0, 1], index_col=0)
    df.index.name = "Date"
    df.index = pd.to_datetime(df.index)
    return df[("Close", ticker.upper())]


def plot(ticker, close):
    """Plot closing prices and return the figure."""
    fig = plt.figure(figsize=(12, 6))
    plt.plot(close.index, close.values)
    plt.title(f"{ticker.upper()} — Daily Close")
    plt.xlabel("Date")
    plt.ylabel("Price ($)")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "uuuu"
    csv_file = f"{ticker}_prices.csv"
    close = load_csv(csv_file, ticker)
    fig = plot(ticker, close)
    out = f"{ticker}_prices.png"
    fig.savefig(out, dpi=150)
    print(f"Saved {out}")
