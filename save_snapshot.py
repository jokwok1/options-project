import os
import pandas as pd
from datetime import date


def save_snapshot(ticker_data, path="iv_history.csv"):
    today = date.today().isoformat()
    rows = []
    for ticker, e in ticker_data.items():
        rows.append({
            "date": today,
            "ticker": ticker,
            "price": e.get("price"),
            "atm_iv": e.get("atm_iv"),
            "hist_vol": e.get("hist_vol"),
            "iv_hv_ratio": e.get("iv_hv_ratio"),
            "expiry": e.get("expiry_used"),
            "strike": e.get("strike"),
        })
    new = pd.DataFrame(rows)

    if not os.path.exists(path):
        new.to_csv(path, index=False)
        return

    old = pd.read_csv(path)
    old = old[~((old["date"] == today) & old["ticker"].isin(new["ticker"]))]
    pd.concat([old, new], ignore_index=True).to_csv(path, index=False)
