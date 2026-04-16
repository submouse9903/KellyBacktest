"""게만아-트레이딩 Docker MySQL DB 연결 모듈"""

from typing import Optional

import pandas as pd
import pymysql

# Docker Compose에서 노출된 MySQL 설정 (Windows 호스트 -> Docker container)
DEFAULT_DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3307,
    "user": "trader",
    "password": "trader",
    "database": "trading",
    "charset": "utf8mb4",
}


def _get_connection():
    return pymysql.connect(**DEFAULT_DB_CONFIG)


def check_connection() -> bool:
    """DB 연결 가능 여부 확인"""
    try:
        conn = _get_connection()
        conn.close()
        return True
    except Exception:
        return False


def get_available_symbols(market: str = "KR") -> pd.DataFrame:
    """DB에 수집된 종목 목록 조회

    Returns:
        DataFrame [symbol, name, market, exchange]
    """
    query = """
        SELECT DISTINCT
            a.symbol,
            a.name,
            a.market,
            a.exchange
        FROM assets a
        JOIN price_candles pc ON pc.asset_id = a.id
        WHERE a.market = %s
          AND pc.timeframe = '1d'
        ORDER BY a.symbol
    """
    conn = _get_connection()
    try:
        df = pd.read_sql(query, conn, params=(market,))
        return df
    finally:
        conn.close()


def get_prices_from_db(
    symbols: list[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    timeframe: str = "1d",
) -> pd.DataFrame:
    """DB에서 선택한 종목의 종가를 wide-form DataFrame으로 조회

    Args:
        symbols: 종목 코드 리스트 (예: ['005930', '000660'])
        start_date: 시작일 (YYYY-MM-DD), None이면 전체
        end_date: 종료일 (YYYY-MM-DD), None이면 전체
        timeframe: 캔들 주기 (기본 '1d')

    Returns:
        DataFrame (index=date, columns=symbol)
    """
    if not symbols:
        return pd.DataFrame()

    # 동적 IN 절 플레이스홀더
    placeholders = ", ".join(["%s"] * len(symbols))

    date_filter = ""
    params: list = [timeframe] + symbols

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

    conn = _get_connection()
    try:
        df = pd.read_sql(query, conn, params=params)
    finally:
        conn.close()

    if df.empty:
        return pd.DataFrame()

    # Wide-form 피벗
    df["date"] = pd.to_datetime(df["date"])
    wide = df.pivot(index="date", columns="symbol", values="close")
    wide = wide.sort_index()

    return wide
