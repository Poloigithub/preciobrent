#!/usr/bin/env python3
"""
Brent crude oil price tracker.

Data source: FRED (Federal Reserve Bank of St. Louis) series DCOILBRENTEU.
Requires env var FRED_API_KEY (free at https://fredaccount.stlouisfed.org/).

Modes:
  init    Download full historical data and generate chart.
  update  Append today's price to the CSV and regenerate chart (run daily at 7 AM).
"""

import argparse
import os
import sys
from datetime import datetime, date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import pytz
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES = "DCOILBRENTEU"   # Brent crude oil, USD/barrel, daily
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

def _api_key() -> str:
    key = os.environ.get("FRED_API_KEY", "")
    if not key:
        raise RuntimeError("FRED_API_KEY environment variable not set.")
    return key


def _fred_get(params: dict) -> list[dict]:
    """Call FRED and return the observations list."""
    params.update({"api_key": _api_key(), "file_type": "json", "series_id": FRED_SERIES})
    resp = requests.get(FRED_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()["observations"]


def fetch_history(start: str = "2019-01-01") -> pd.DataFrame:
    """Download full daily closing price history from FRED."""
    obs = _fred_get({"observation_start": start, "sort_order": "asc"})
    records = [
        (o["date"], float(o["value"]))
        for o in obs
        if o["value"] != "."   # FRED uses "." for missing values
    ]
    df = pd.DataFrame(records, columns=["Date", "USD"])
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date")
    df.index.name = "Date"
    return df


def load_csv() -> pd.DataFrame:
    return pd.read_csv(CSV_FILE, parse_dates=["Date"], index_col="Date")


def save_csv(df: pd.DataFrame) -> None:
    df.to_csv(CSV_FILE, date_format="%Y-%m-%d")


def fetch_latest_price() -> tuple[date, float]:
    """Return (date, price) for the most recent available trading day."""
    obs = _fred_get({"sort_order": "desc", "limit": "10"})
    for o in obs:
        if o["value"] != ".":
            last_date = datetime.strptime(o["date"], "%Y-%m-%d").date()
            return last_date, round(float(o["value"]), 2)
    raise RuntimeError("No valid price data found in FRED response.")


# ---------------------------------------------------------------------------
# Chart generation
# ---------------------------------------------------------------------------

def generate_chart(df: pd.DataFrame) -> None:
    now_madrid = datetime.now(TIMEZONE)
    time_str = now_madrid.strftime("%H:%M")
    last_price = df["USD"].iloc[-1]
    subtitle = f"Último dato tomado a las {time_str} hora española · ${last_price:.2f}"

    fig, ax = plt.subplots(figsize=(13, 7))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.plot(df.index, df["USD"], color="#555555", linewidth=0.9)

    ax.yaxis.grid(True, color="#cccccc", linewidth=0.7)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)

    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#cccccc")

    ax.tick_params(axis="both", which="both", length=0, labelsize=9, colors="#444444")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x)}"))

    ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%-m/%d\n%Y"))
    plt.setp(ax.get_xticklabels(), ha="center", fontsize=7.5)

    ax.set_ylabel(Y_LABEL, fontsize=9, color="#444444", labelpad=6)

    fig.text(0.5, 0.97, CHART_TITLE,
             ha="center", va="top", fontsize=15, fontweight="bold", color="#111111")
    fig.text(0.5, 0.92, subtitle,
             ha="center", va="top", fontsize=11, color="#3399cc")

    ax.plot([], [], color="#555555", linewidth=4, label="USD")
    legend = ax.legend(loc="lower left", frameon=False, fontsize=9,
                       handlelength=1.5, handleheight=0.8)
    legend.get_texts()[0].set_color("#333333")

    fig.text(0.99, 0.01, SOURCE_TEXT,
             ha="right", va="bottom", fontsize=8.5, color="#333333", fontstyle="italic")
    fig.text(0.01, 0.01, CHART_CREDIT,
             ha="left", va="bottom", fontsize=8.5, color="#333333", fontstyle="italic")

    plt.tight_layout(rect=[0, 0.02, 1, 0.91])
    plt.savefig(CHART_FILE, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Chart saved → {CHART_FILE}")


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def cmd_init(args) -> None:
    start = args.start if hasattr(args, "start") and args.start else "2019-01-01"
    print(f"Downloading Brent price history from {start} (FRED)…")
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
