# Options Project

Personal quant toolkit for wheel-strategy options/volatility analysis.
Data source: Yahoo Finance via `yfinance` (free, ~15 min delayed). No paid APIs.

## Overview

| File | Purpose |
|---|---|
| `plot_gui.py` | Tkinter GUI: price chart + EMA50, realized-vol panel, ticker table, action alert banner |
| `screener.py` | Scans the watchlist, computes alerts, writes the Telegram message (`daily_message.txt`) |
| `yf_data.py` | Price/earnings fetching + shared `compute_ema50_rsi` helper |
| `fetch_iv.py` | Option chain, ATM IV (Black-Scholes), IV/HV ratio |
| `save_snapshot.py` | Appends daily IV/HV snapshot to `iv_history.csv` |
| `notify.py` | Sends `daily_message.txt` to a Telegram chat |
| `realized_vol.py` | Two-panel PNG (price + 30d realized vol) from saved CSVs |
| `plot_prices.py` | Simple single-panel price PNG |
| `watchlist.txt` | One ticker per line |

## Setup

```powershell
uv sync                # installs deps into .venv (Python 3.12+)
```

## Usage

### GUI

```powershell
uv run python plot_gui.py
```

- Loads `watchlist.txt` automatically.
- **Ticker Overview table**: ticker, price, next earnings, days away, ATM IV,
  IV/HV, hist vol, RSI, 52W high, EPS/Rev est, expiry.
- **Chart**: daily close + EMA50 overlay on top, 30-day realized vol below.
- **Action alert banner**: red strip when any ticker is flagged, green otherwise.

### CLI screener + Telegram

```powershell
uv run python screener.py            # scans watchlist.txt
uv run python screener.py UUUU UEC   # specific tickers (space-separated)

uv run python notify.py              # sends daily_message.txt to Telegram
```

The screener writes `daily_message.txt` (HTML for Telegram) and appends a
snapshot to `iv_history.csv`. The notify script requires env vars:

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

## Indicator definitions

- **EMA50**: exponential moving average, span 50, `adjust=False`.
- **RSI(14)**: Wilder's RSI using `ewm(alpha=1/14, min_periods=14)`.
- **Realized vol (HV)**: std of log returns over 30 days, annualized (`* sqrt(252)`).
- **ATM IV**: Black-Scholes implied vol of the closest-to-spot put with
  volume/lastPrice > 0, on the option expiry nearest ~30 days out.
- **IV/HV ratio**: `ATM IV / realized vol`. > 1 means options are pricing in
  more movement than the stock has realized.

Both the GUI and screener compute EMA50/RSI via the shared
`yf_data.compute_ema50_rsi(close)` so results match everywhere.

## Action alert rules

A ticker is flagged when it hits **any** of these independent rules
(`screener.flag_reasons`):

| Rule | Condition | Alert text |
|---|---|---|
| Rich IV | IV/HV ≥ 1.5 | `IV/HV 1.69x` |
| Weak momentum | close < EMA50 **and** RSI ≤ 40 | `close<EMA50 ($13.00), RSI 38.2` |
| Earnings soon | next earnings within 5 days | `earnings in 3d` |

Thresholds are constants at the top of `screener.py`:

```python
FLAG_IV_HV_MIN = 1.5
FLAG_RSI_MAX = 40
FLAG_EARNINGS_DAYS = 5
```

The same logic powers the GUI banner and the Telegram ACTION ALERT line, so
both stay in sync.

## Telegram message

`daily_message.txt` contains:

1. Optional `🚨 ACTION ALERT 🚨` banner listing flagged tickers + reasons.
2. `IV Screener` header with date.
3. Fixed-width table (monospace) with columns:
   **Ticker, Price, Earnings, Days, ATM IV, IV/HV, HistVol, 52WHigh, EMA, RSI**.

Flagged tickers are bolded in the table.

## Workflow (typical daily run)

```powershell
uv run python screener.py              # analyze watchlist, write message + snapshot
uv run python notify.py                # push to Telegram
```

Or just open the GUI for the bird's-eye view and per-ticker charts.

## Technical indicator scripts (skill)

The `technical-analysis` skill ships standalone scripts that use `pandas-ta`:

```powershell
uv run python .agents/skills/technical-analysis/scripts/technicals.py UUUU,UEC
uv run python .agents/skills/technical-analysis/scripts/correlation.py UUUU,UEC,SILJ
```

These compute EMA9/12/21/26, MACD, Bollinger, SMA, ATR, ADX, plus crossovers.
