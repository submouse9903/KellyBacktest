"""MySQL KRX 데이터를 Lean Local Data 포맷으로 변환"""

import json
import os
import sys
import zipfile
from pathlib import Path

import pandas as pd
import pymysql

# 프로젝트 루트 기준
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "equity" / "usa" / "daily"

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3307,
    "user": "trader",
    "password": "trader",
    "database": "trading",
    "charset": "utf8mb4",
}


def fetch_prices(symbols: list[str], start_date: str, end_date: str) -> pd.DataFrame:
    """DB에서 종가 데이터를 wide-form DataFrame으로 조회"""
    if not symbols:
        return pd.DataFrame()

    placeholders = ", ".join(["%s"] * len(symbols))
    params: list = ["1d"] + symbols

    date_filter = ""
    if start_date:
        date_filter += " AND pc.ts >= %s"
        params.append(start_date)
    if end_date:
        date_filter += " AND pc.ts <= %s"
        params.append(end_date)

    query = f"""
        SELECT
            DATE(pc.ts) AS date,
            a.symbol,
            CAST(pc.close AS DOUBLE) AS close
        FROM price_candles pc
        JOIN assets a ON a.id = pc.asset_id
        WHERE pc.timeframe = %s
          AND a.symbol IN ({placeholders})
          {date_filter}
        ORDER BY date, a.symbol
    """

    conn = pymysql.connect(**DB_CONFIG)
    try:
        df = pd.read_sql(query, conn, params=params)
    finally:
        conn.close()

    if df.empty:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"])
    wide = df.pivot(index="date", columns="symbol", values="close")
    wide = wide.sort_index()
    return wide


def to_lean_csv(prices: pd.Series, symbol: str, out_dir: Path) -> Path:
    """종가 시리즈를 Lean Equity Daily CSV로 저장

    Lean은 OHLCV를 기대하므로 close를 open/high/low에 복제하고 volume=0
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame({
        "date": prices.index.strftime("%Y-%m-%d"),
        "open": prices.values,
        "high": prices.values,
        "low": prices.values,
        "close": prices.values,
        "volume": 0,
    })
    path = out_dir / f"{symbol.lower()}.csv"
    df.to_csv(path, index=False)
    return path


def export_symbols(
    symbols: list[str],
    start_date: str,
    end_date: str,
    out_dir: Path = DATA_DIR,
) -> dict[str, Path]:
    """여러 심볼을 한 번에 Export"""
    wide = fetch_prices(symbols, start_date, end_date)
    if wide.empty:
        return {}

    results = {}
    for symbol in symbols:
        if symbol in wide.columns:
            path = to_lean_csv(wide[symbol].dropna(), symbol, out_dir)
            results[symbol] = path
            print(f"Exported {symbol} -> {path}")
    return results


if __name__ == "__main__":
    export_symbols(
        symbols=["005930"],
        start_date="2020-01-01",
        end_date="2024-12-31",
    )
