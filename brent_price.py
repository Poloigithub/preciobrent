#!/usr/bin/env python3
"""
Brent crude oil price tracker.

Data source: Yahoo Finance via yfinance (ticker BZ=F).

Modes:
  init    Download full historical data and generate chart.
  update  Append today's price to the CSV and regenerate chart (run daily at 7 AM).
"""

import argparse
import os
import sys
import time
from datetime import datetime, date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import pytz
import yfinance as yf

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TICKER = "BZ=F"          # Brent crude futures on Yahoo Finance
CSV_FILE = "brent_prices.csv"
CHART_FILE = "brent_chart.png"
TIMEZONE = pytz.timezone("Europe/Madrid")

# Chart style constants
CHART_TITLE = "Evolución del precio del barril de Brent"
Y_LABEL = "Dólares estadounidenses (USD)"
SOURCE_TEXT = "Fuente: Yahoo Finance"
CHART_CREDIT = "Gráfico: @poloi.eurosky.social"


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _yf_download(ticker: yf.Ticker, **kwargs) -> pd.DataFrame:
    """Call ticker.history() with up to 3 retries on rate-limit errors."""
    for attempt in range(3):
        try:
            df = ticker.history(**kwargs)
            if not df.empty:
                return df
        except Exception as exc:
            if attempt == 2:
                raise
            wait = 10 * (attempt + 1)   # 10s, 20s
            print(f"Attempt {attempt + 1} failed ({exc}). Retrying in {wait}s…")
            time.sleep(wait)
    raise RuntimeError("Yahoo Finance returned empty data after 3 attempts.")


def fetch_history(start: str = "2019-01-01") -> pd.DataFrame:
    """Download daily closing prices from Yahoo Finance."""
    ticker = yf.Ticker(TICKER)
    df = _yf_download(ticker, start=start, auto_adjust=True)
    df = df[["Close"]].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "Date"
    df.rename(columns={"Close": "USD"}, inplace=True)
    return df


def load_csv() -> pd.DataFrame:
    return pd.read_csv(CSV_FILE, parse_dates=["Date"], index_col="Date")


def save_csv(df: pd.DataFrame) -> None:
    df.to_csv(CSV_FILE, date_format="%Y-%m-%d")


def fetch_latest_price() -> tuple[date, float]:
    """Return (date, close_price) for the most recent available trading day."""
    ticker = yf.Ticker(TICKER)
    df = _yf_download(ticker, period="5d", auto_adjust=True)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    last_date = df.index[-1].date()
    return last_date, round(float(df["Close"].iloc[-1]), 2)


# ---------------------------------------------------------------------------
# Chart generation
# ---------------------------------------------------------------------------

# Design tokens
LINE_COLOR    = "#1565c0"   # deep blue line
FILL_COLOR    = "#1565c0"   # same for fill
DOT_COLOR     = "#1565c0"
LABEL_BG      = "#1565c0"
GRID_COLOR    = "#e8edf2"
SPINE_COLOR   = "#d0d8e0"
TICK_COLOR    = "#6b7c93"
TITLE_COLOR   = "#0d1b2a"
SUBTITLE_COLOR = "#1565c0"
CREDIT_COLOR  = "#8a9bb0"
BG_COLOR      = "#f8fafc"   # very subtle off-white background


def generate_chart(df: pd.DataFrame) -> None:
    now_madrid = datetime.now(TIMEZONE)
    date_str  = now_madrid.strftime("%-d de %B de %Y").lower()
    time_str  = now_madrid.strftime("%H:%M")
    last_price = df["USD"].iloc[-1]
    last_date  = df.index[-1]

    subtitle = (
        f"Último dato: {date_str} · {time_str} hora española · "
        f"${last_price:.2f} / barril"
    )

    fig, ax = plt.subplots(figsize=(13, 7))
    fig.patch.set_facecolor("white")
    ax.set_facecolor(BG_COLOR)

    # Fill under the line
    ax.fill_between(df.index, df["USD"],
                    alpha=0.08, color=FILL_COLOR, linewidth=0)

    # Main line
    ax.plot(df.index, df["USD"],
            color=LINE_COLOR, linewidth=1.4, zorder=3)

    # Dot at last price
    ax.scatter([last_date], [last_price],
               color=DOT_COLOR, s=55, zorder=5, linewidths=0)

    # Price badge next to dot
    ax.annotate(
        f"  ${last_price:.2f}",
        xy=(last_date, last_price),
        xytext=(6, 0), textcoords="offset points",
        fontsize=9.5, fontweight="bold", color=LABEL_BG,
        va="center",
    )

    # Dashed horizontal line at current price
    ax.axhline(last_price, color=LINE_COLOR, linewidth=0.6,
               linestyle="--", alpha=0.35, zorder=1)

    # Grid
    ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.8)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)

    # Spines
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(SPINE_COLOR)

    # Ticks
    ax.tick_params(axis="both", which="both", length=0,
                   labelsize=9, colors=TICK_COLOR)
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"${int(x)}")
    )

    # X-axis: quarterly labels
    ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b\n%Y"))
    plt.setp(ax.get_xticklabels(), ha="center", fontsize=8, color=TICK_COLOR)

    # Y-label
    ax.set_ylabel(Y_LABEL, fontsize=9, color=TICK_COLOR, labelpad=8)

    # Padding so the price badge doesn't get clipped
    xmin, xmax = ax.get_xlim()
    ax.set_xlim(xmin, xmax + (xmax - xmin) * 0.04)

    # Titles
    fig.text(0.5, 0.97, CHART_TITLE,
             ha="center", va="top", fontsize=16,
             fontweight="bold", color=TITLE_COLOR)
    fig.text(0.5, 0.92, subtitle,
             ha="center", va="top", fontsize=10.5, color=SUBTITLE_COLOR)

    # Legend
    ax.plot([], [], color=LINE_COLOR, linewidth=3, label="Brent USD/barril")
    legend = ax.legend(loc="upper left", frameon=False, fontsize=9)
    legend.get_texts()[0].set_color(TICK_COLOR)

    # Credits
    fig.text(0.99, 0.01, SOURCE_TEXT,
             ha="right", va="bottom", fontsize=8, color=CREDIT_COLOR,
             fontstyle="italic")
    fig.text(0.01, 0.01, CHART_CREDIT,
             ha="left", va="bottom", fontsize=8, color=CREDIT_COLOR,
             fontstyle="italic")

    plt.tight_layout(rect=[0, 0.025, 1, 0.905])
    plt.savefig(CHART_FILE, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Chart saved → {CHART_FILE}")


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def cmd_init(args) -> None:
    start = args.start if hasattr(args, "start") and args.start else "2019-01-01"
    print(f"Downloading Brent price history from {start} (Yahoo Finance)…")
    df = fetch_history(start=start)
    save_csv(df)
    print(f"CSV saved → {CSV_FILE}  ({len(df)} rows)")
    generate_chart(df)


def cmd_update(args) -> None:
    if not os.path.exists(CSV_FILE):
        print(f"CSV not found ({CSV_FILE}). Run with init first.", file=sys.stderr)
        sys.exit(1)

    df = load_csv()
    today, price = fetch_latest_price()
    today_ts = pd.Timestamp(today)

    if today_ts in df.index:
        df.loc[today_ts, "USD"] = price
        print(f"Updated existing entry: {today} → ${price}")
    else:
        new_row = pd.DataFrame({"USD": [price]}, index=[today_ts])
        new_row.index.name = "Date"
        df = pd.concat([df, new_row])
        print(f"Added new entry: {today} → ${price}")

    df.sort_index(inplace=True)
    save_csv(df)
    generate_chart(df)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Brent oil price tracker.")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Download full history and generate chart.")
    p_init.add_argument("--start", default="2019-01-01",
                        help="Start date (YYYY-MM-DD). Default: 2019-01-01")
    p_init.set_defaults(func=cmd_init)

    p_update = sub.add_parser("update", help="Append today's price and regenerate chart.")
    p_update.set_defaults(func=cmd_update)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
