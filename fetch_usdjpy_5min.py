#!/usr/bin/env python3
"""指定日(デフォルトは前日、日本時間の暦日)のUSDJPY 5分足OHLCをyfinanceから取得し、
output/usdjpy_5min_<YYYYMMDD>.csv に保存する。

このスクリプトはデータ取得のみを行う。値動きの検出・ニュース調査・チャート描画は
このスクリプトを呼び出す側(スケジュール実行されるClaudeセッション)が担当する。

使い方:
    python fetch_usdjpy_5min.py                # 前日(JST)のデータを取得
    python fetch_usdjpy_5min.py --date 2026-08-12  # 対象日を指定
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

TICKER = "JPY=X"
INTERVAL = "5m"
TZ = ZoneInfo("Asia/Tokyo")
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def parse_args():
    parser = argparse.ArgumentParser(description="USDJPY 5分足データ取得")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="対象日 (YYYY-MM-DD, JST暦日)。省略時は前日。",
    )
    return parser.parse_args()


def resolve_target_date(date_str):
    if date_str:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    today_jst = datetime.now(TZ).date()
    return today_jst - timedelta(days=1)


def fetch_5min_data(target_date):
    day_start = datetime.combine(target_date, datetime.min.time(), tzinfo=TZ)
    day_end = day_start + timedelta(days=1)

    # yfinanceの5分足は直近60日以内のみ取得可能。対象日の前後に余裕を持たせて取得し、
    # 取得後にJSTの暦日境界で厳密にフィルタする。
    fetch_start = day_start - timedelta(days=1)
    fetch_end = day_end + timedelta(days=1)

    df = yf.download(
        TICKER,
        interval=INTERVAL,
        start=fetch_start,
        end=fetch_end,
        progress=False,
        auto_adjust=False,
    )

    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert(TZ)

    df = df[(df.index >= day_start) & (df.index < day_end)]

    return df[["Open", "High", "Low", "Close"]]


def main():
    args = parse_args()
    target_date = resolve_target_date(args.date)

    print(f"対象日 (JST): {target_date.isoformat()}")
    df = fetch_5min_data(target_date)

    if df.empty:
        print(
            f"警告: {target_date.isoformat()} のUSDJPY 5分足データが取得できませんでした。"
            f"休場日(週末など)か、取得可能範囲外(60日より前)の可能性があります。"
        )
        sys.exit(0)

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"usdjpy_5min_{target_date.strftime('%Y%m%d')}.csv"
    df.to_csv(out_path, index_label="datetime_jst")

    print(f"保存先: {out_path}")
    print(f"件数: {len(df)} 本")
    print(f"期間: {df.index.min()} 〜 {df.index.max()}")


if __name__ == "__main__":
    main()
