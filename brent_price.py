#!/usr/bin/env python3
"""
Brent crude oil price tracker.

Modes:
  --init    Download full historical data and generate chart.
  --update  Append today's price to the CSV and regenerate chart (run daily at 7 AM).
"""

import argparse
import csv
import os
import sys
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

def fetch_history(start: str = "2019-01-01") -> pd.DataFrame:
    """Download daily closing prices from Yahoo Finance."""
    ticker = yf.Ticker(TICKER)
    df = ticker.history(start=start, auto_adjust=True)
    if df.empty:
        raise RuntimeError("Yahoo Finance returned empty data. Check ticker or network.")
    df = df[["Close"]].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)  # strip tz for simplicity
    df.index.name = "Date"
    df.rename(columns={"Close": "USD"}, inplace=True)
    return df


def load_csv() -> pd.DataFrame:
    """Load existing CSV into a DataFrame indexed by date."""
    df = pd.read_csv(CSV_FILE, parse_dates=["Date"], index_col="Date")
    return df


def save_csv(df: pd.DataFrame) -> None:
    """Save DataFrame to CSV with Date and USD columns."""
    df.to_csv(CSV_FILE, date_format="%Y-%m-%d")


def fetch_latest_price() -> tuple[date, float]:
    """Return (date, close_price) for the most recent available trading day."""
    ticker = yf.Ticker(TICKER)
    # period="5d" ensures we get the last closed day even near weekends/holidays
    df = ticker.history(period="5d", auto_adjust=True)
    if df.empty:
        raise RuntimeError("Could not fetch latest price from Yahoo Finance.")
    last_row = df.iloc[-1]
    last_date = pd.to_datetime(df.index[-1]).date()
    return last_date, round(float(last_row["Close"]), 2)


# ---------------------------------------------------------------------------
# Chart generation
# ---------------------------------------------------------------------------

def generate_chart(df: pd.DataFrame) -> None:
    """Recreate the Brent price evolution chart and save it as PNG."""
    now_madrid = datetime.now(TIMEZONE)
    time_str = now_madrid.strftime("%H:%M")
    subtitle = f"Último dato tomado a las {time_str} hora española"

    fig, ax = plt.subplots(figsize=(13, 7))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # Plot line
    ax.plot(df.index, df["USD"], color="#555555", linewidth=0.9)

    # Grid – horizontal only, light gray
    ax.yaxis.grid(True, color="#cccccc", linewidth=0.7)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)

    # Remove spines except bottom
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#cccccc")

    # Ticks
    ax.tick_params(axis="both", which="both", length=0, labelsize=9, colors="#444444")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x)}"))

    # X-axis: show one label per quarter (approx every 3 months)
    ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%-m/%d\n%Y"))
    plt.setp(ax.get_xticklabels(), ha="center", fontsize=7.5)

    # Labels
    ax.set_ylabel(Y_LABEL, fontsize=9, color="#444444", labelpad=6)

    # Titles
    fig.text(
        0.5, 0.97, CHART_TITLE,
        ha="center", va="top", fontsize=15, fontweight="bold", color="#111111"
    )
    fig.text(
        0.5, 0.92, subtitle,
        ha="center", va="top", fontsize=11, color="#3399cc"
    )

    # Legend / source
    ax.plot([], [], color="#555555", linewidth=4, label="USD")
    legend = ax.legend(
        loc="lower left", frameon=False, fontsize=9,
        handlelength=1.5, handleheight=0.8
    )
    legend.get_texts()[0].set_color("#333333")

    fig.text(
        0.99, 0.01, SOURCE_TEXT,
        ha="right", va="bottom", fontsize=8.5, color="#333333",
        fontstyle="italic"
    )
    fig.text(
        0.01, 0.01, CHART_CREDIT,
        ha="left", va="bottom", fontsize=8.5, color="#333333",
        fontstyle="italic"
    )

    # Layout
    plt.tight_layout(rect=[0, 0.02, 1, 0.91])
    plt.savefig(CHART_FILE, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Chart saved → {CHART_FILE}")


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def cmd_init(args) -> None:
    """Download full history, save CSV, generate chart."""
    start = args.start if hasattr(args, "start") and args.start else "2019-01-01"
    print(f"Downloading Brent price history from {start}…")
    df = fetch_history(start=start)
    save_csv(df)
    print(f"CSV saved → {CSV_FILE}  ({len(df)} rows)")
    generate_chart(df)


def cmd_update(args) -> None:
    """Append today's price (if new) to the CSV and regenerate chart."""
    if not os.path.exists(CSV_FILE):
        print(f"CSV not found ({CSV_FILE}). Run with --init first.", file=sys.stderr)
        sys.exit(1)

    df = load_csv()
    today, price = fetch_latest_price()
    today_ts = pd.Timestamp(today)

    if today_ts in df.index:
        # Update value in case it changed during the day
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
    parser = argparse.ArgumentParser(
        description="Brent oil price tracker – fetch, store, and chart."
    )
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Download full history and generate chart.")
    p_init.add_argument(
        "--start", default="2019-01-01",
        help="Start date for historical download (YYYY-MM-DD). Default: 2019-01-01"
    )
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
