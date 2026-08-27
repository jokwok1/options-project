import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib
import numpy as np

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from fetch_iv import compute_iv_hv_ratio, find_atm_iv, get_option_chain
from save_snapshot import save_snapshot
from screener import flag_reasons
from yf_data import compute_ema50_rsi, fetch, fetch_earnings_info


class TickerApp:
    def __init__(self, root):
        self.root = root
        amp = chr(38)
        self.root.title("Options Analysis \u2014 Price Charts " + amp + " Earnings")
        self.root.geometry("1200x800")

        self.ticker_data = {}
        self.selected_ticker = None
        self.canvas_widget = None
        self._sort_col = "iv_hv"
        self._sort_rev = True

        self._build_ui()
        self._update_alert()
        self.root.after(100, self._load_watchlist)

    def _build_ui(self):
        top = tk.Frame(self.root)
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        tk.Label(top, text="Ticker:").pack(side=tk.LEFT)
        self.entry = tk.Entry(top, width=10)
        self.entry.pack(side=tk.LEFT, padx=(5, 10))
        self.entry.insert(0, "")
        self.entry.bind("<Return>", lambda e: self.add_ticker())

        tk.Button(top, text="Add", command=self.add_ticker).pack(side=tk.LEFT)
        tk.Button(
            top, text="Remove", command=self.remove_ticker
        ).pack(side=tk.LEFT, padx=(5, 0))

        self.status = tk.Label(top, text="", fg="gray")
        self.status.pack(side=tk.LEFT, padx=20)

        self.alert = tk.Label(
            self.root, text="", anchor=tk.W, padx=10, pady=5,
            font=("Consolas", 10, "bold"),
        )
        self.alert.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 5))

        table_frame = tk.LabelFrame(self.root, text="Ticker Overview", padx=5, pady=5)
        table_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 5))

        cols = (
            "ticker", "price", "earnings_date", "days_away",
            "atm_iv", "iv_hv", "hist_vol", "rsi", "high_52w",
            "eps_est", "rev_est", "expiry",
        )
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=4)

        self.tree.heading("ticker", text="Ticker")
        self.tree.heading("price", text="Price")
        self.tree.heading("earnings_date", text="Next Earnings")
        self.tree.heading("days_away", text="Days Away")
        self.tree.heading("atm_iv", text="ATM IV")
        self.tree.heading("iv_hv", text="IV/HV")
        self.tree.heading("hist_vol", text="Hist Vol")
        self.tree.heading("rsi", text="RSI")
        self.tree.heading("high_52w", text="52W High")
        self.tree.heading("eps_est", text="EPS Est")
        self.tree.heading("rev_est", text="Rev Est")
        self.tree.heading("expiry", text="Expiry")

        self.tree.column("ticker", width=70, anchor=tk.CENTER)
        self.tree.column("price", width=80, anchor=tk.CENTER)
        self.tree.column("earnings_date", width=100, anchor=tk.CENTER)
        self.tree.column("days_away", width=70, anchor=tk.CENTER)
        self.tree.column("atm_iv", width=80, anchor=tk.CENTER)
        self.tree.column("iv_hv", width=70, anchor=tk.CENTER)
        self.tree.column("hist_vol", width=80, anchor=tk.CENTER)
        self.tree.column("rsi", width=50, anchor=tk.CENTER)
        self.tree.column("high_52w", width=80, anchor=tk.CENTER)
        self.tree.column("eps_est", width=80, anchor=tk.CENTER)
        self.tree.column("rev_est", width=100, anchor=tk.CENTER)
        self.tree.column("expiry", width=100, anchor=tk.CENTER)

        self.tree.pack(fill=tk.X)
        self.tree.bind("<<TreeviewSelect>>", self._on_table_select)
        for col in cols:
            self.tree.heading(col, command=lambda c=col: self._sort_by_column(c))

        bottom = tk.Frame(self.root)
        bottom.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        sidebar = tk.LabelFrame(bottom, text="Tickers", padx=5, pady=5)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        self.ticker_listbox = tk.Listbox(sidebar, width=12, font=("Consolas", 11))
        self.ticker_listbox.pack(fill=tk.BOTH, expand=True)
        self.ticker_listbox.bind("<<ListboxSelect>>", self._on_listbox_select)

        chart_frame = tk.Frame(bottom)
        chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.info_label = tk.Label(
            chart_frame, text="", justify=tk.LEFT, anchor=tk.W,
            font=("Consolas", 10), padx=10, pady=5
        )
        self.info_label.pack(fill=tk.X)

        self.chart_frame = tk.Frame(chart_frame)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)

    def add_ticker(self, save=True):
        ticker = self.entry.get().strip().upper()
        if not ticker:
            messagebox.showwarning("Input", "Enter a ticker symbol")
            return
        if ticker in self.ticker_data:
            self.status.config(text=f"{ticker} already added")
            return

        self.status.config(text=f"Fetching {ticker}...")
        self.root.update()

        data = fetch(ticker)
        if data.empty:
            self.status.config(text="")
            messagebox.showerror("Error", f"No data returned for {ticker}")
            return

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
            spot, expiry, chain = get_option_chain(ticker)
            price = spot
            expiry_used = expiry
            strike, atm_iv = find_atm_iv(chain, spot, expiry)
        except Exception:
            pass

        if price is None:
            price = close.iloc[-1]

        iv_hv_ratio = compute_iv_hv_ratio(atm_iv, hist_vol)

        self.ticker_data[ticker] = {
            "data": data,
            "earnings": earnings,
            "price": price,
            "close": close.iloc[-1],
            "ema50": ema50.iloc[-1],
            "rsi": rsi.iloc[-1],
            "atm_iv": atm_iv,
            "hist_vol": hist_vol,
            "iv_hv_ratio": iv_hv_ratio,
            "expiry_used": expiry_used,
            "strike": strike,
        }

        self.ticker_listbox.insert(tk.END, ticker)
        self._update_earnings_table()
        self._update_alert()
        self._select_ticker(ticker)
        self.entry.delete(0, tk.END)
        self.status.config(text=f"Added {ticker}")
        if save:
            save_snapshot(self.ticker_data)

    def remove_ticker(self):
        sel = self.ticker_listbox.curselection()
        if not sel:
            return
        ticker = self.ticker_listbox.get(sel[0])
        self.ticker_listbox.delete(sel[0])
        del self.ticker_data[ticker]
        self._update_earnings_table()
        self._update_alert()

        if self.selected_ticker == ticker:
            self.selected_ticker = None
            self.info_label.config(text="")
            if self.canvas_widget:
                self.canvas_widget.get_tk_widget().destroy()
                self.canvas_widget = None

        if self.ticker_listbox.size() > 0:
            self.ticker_listbox.selection_set(0)
            self._on_listbox_select(None)

    def _select_ticker(self, ticker):
        self.selected_ticker = ticker
        for i in range(self.ticker_listbox.size()):
            if self.ticker_listbox.get(i) == ticker:
                self.ticker_listbox.selection_clear(0, tk.END)
                self.ticker_listbox.selection_set(i)
                break
        self._show_chart(ticker)

    def _on_listbox_select(self, event):
        sel = self.ticker_listbox.curselection()
        if not sel:
            return
        ticker = self.ticker_listbox.get(sel[0])
        self._select_ticker(ticker)

    def _on_table_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        ticker = item["values"][0]
        self._select_ticker(ticker)

    def _show_chart(self, ticker):
        entry = self.ticker_data.get(ticker)
        if not entry:
            return

        data = entry["data"]
        earnings = entry["earnings"]
        close = data[("Close", ticker)]
        ema50, rsi = compute_ema50_rsi(close)

        returns = np.log(close / close.shift(1))
        vol = returns.rolling(30).std() * np.sqrt(252)

        current_rsi = rsi.iloc[-1]
        rsi_str = f"{current_rsi:.1f}" if not np.isnan(current_rsi) else "N/A"

        current_vol = vol.iloc[-1]
        vol_str = f"{current_vol:.0%}" if not np.isnan(current_vol) else "N/A"
        atm_iv = entry["atm_iv"]
        atm_iv_str = f"{atm_iv:.1%}" if atm_iv is not None else "N/A"
        ratio = entry.get("iv_hv_ratio")
        ratio_str = f"{ratio:.2f}x" if ratio is not None else "N/A"
        amp = chr(38)
        lines = [
            f"{ticker} \u2014 Daily Close (1Y)",
            f"Next Earnings: {earnings['earnings_date']} ({earnings['days_away']})",
            f"EPS Est: {earnings['eps_est']}  "
                + amp + f"  Rev Est: {earnings['rev_est']}",
            f"52W High: {earnings['high_52w']}  "
                + amp + f"  Realized Vol (30d): {vol_str}",
            f"ATM IV: {atm_iv_str}  "
                + amp + f"  IV/HV Ratio: {ratio_str}",
            f"EMA50: ${ema50.iloc[-1]:.2f}  "
                + amp + f"  RSI(14): {rsi_str}",
        ]
        self.info_label.config(text="\n".join(lines))

        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(10, 5), dpi=100,
            sharex=True,
            gridspec_kw={"height_ratios": [3, 1]},
        )

        ax1.plot(close.index, close.values, linewidth=1.2, label="Close")
        ax1.plot(ema50.index, ema50.values, linewidth=1.2,
                 color="tab:orange", label="EMA50")
        ax1.set_ylabel("Price ($)")
        ax1.set_title(
            f"{ticker} \u2014 Daily Close + EMA50 "
            + amp + " 30-Day Realized Volatility"
        )
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc="upper left")

        ax2.plot(vol.index, vol.values, linewidth=1.2, color="tab:orange")
        ax2.set_ylabel("Realized Vol")
        ax2.set_xlabel("Date")
        ax2.grid(True, alpha=0.3)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))

        fig.autofmt_xdate()
        fig.tight_layout()

        if self.canvas_widget:
            self.canvas_widget.get_tk_widget().destroy()

        self.canvas_widget = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas_widget.draw()
        self.canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _update_earnings_table(self):
        self.tree.delete(*self.tree.get_children())
        items = list(self.ticker_data.items())
        col = self._sort_col
        rev = self._sort_rev

        def sort_key(item):
            ticker, e = item
            if col == "ticker":
                return ticker.lower()
            if col == "iv_hv":
                r = e.get("iv_hv_ratio")
                return r if r is not None else -1
            if col == "atm_iv":
                return e["atm_iv"] if e["atm_iv"] is not None else -1
            if col == "hist_vol":
                return e["hist_vol"] if not np.isnan(e["hist_vol"]) else -1
            if col == "days_away":
                return e["earnings"]["days_away"] if e["earnings"]["days_away"] is not None else 9999
            return ticker.lower()

        items.sort(key=sort_key, reverse=rev)

        for ticker, e in items:
            earnings = e["earnings"]
            price_str = f"${e['price']:.2f}" if e["price"] is not None else "N/A"
            atm_iv_str = f"{e['atm_iv']:.1%}" if e["atm_iv"] is not None else "N/A"
            hv = e["hist_vol"]
            hist_vol_str = f"{hv:.1%}" if not np.isnan(hv) else "N/A"
            ratio = e.get("iv_hv_ratio")
            ratio_str = f"{ratio:.2f}" if ratio is not None else "N/A"
            rsi = e.get("rsi")
            rsi_str = f"{rsi:.1f}" if rsi is not None and not np.isnan(rsi) else "N/A"
            expiry_str = e["expiry_used"] if e["expiry_used"] is not None else "N/A"

            self.tree.insert("", tk.END, values=(
                ticker,
                price_str,
                earnings["earnings_date"],
                earnings["days_away"],
                atm_iv_str,
                ratio_str,
                hist_vol_str,
                rsi_str,
                earnings["high_52w"],
                earnings["eps_est"],
                earnings["rev_est"],
                expiry_str,
            ))


    def _update_alert(self):
        flagged = []
        for ticker, e in self.ticker_data.items():
            for reason in flag_reasons(e):
                flagged.append(f"{ticker} ({reason})")
        if flagged:
            self.alert.config(
                text="\u26a0 ACTION ALERT \u26a0  " + " \u00b7 ".join(flagged),
                bg="#ff4d4d", fg="white",
            )
        else:
            self.alert.config(
                text="\u2705 No action alerts",
                bg="#4caf50", fg="white",
            )


    def _sort_by_column(self, col):
        if self._sort_col == col:
            self._sort_rev = not self._sort_rev
        else:
            self._sort_col = col
            self._sort_rev = False
        self._update_earnings_table()

    def _load_watchlist(self):
        try:
            with open("watchlist.txt") as f:
                tickers = [line.strip().upper() for line in f if line.strip()]
        except FileNotFoundError:
            return
        for t in tickers:
            if t in self.ticker_data:
                continue
            self.entry.insert(0, t)
            self.add_ticker(save=False)
            self.root.update()
        save_snapshot(self.ticker_data)


if __name__ == "__main__":
    root = tk.Tk()
    app = TickerApp(root)
    root.mainloop()
