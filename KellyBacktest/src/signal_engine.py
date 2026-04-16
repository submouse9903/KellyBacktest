"""기술적 분석 기반 매수/매도 상태(State) 생성 엔진

중요: 이 모듈은 시장의 '상태(State)'를 +1, 0, -1로 반환합니다.
      실제 거래 '이벤트(Event)'는 strategy_analyzer의 state_to_events()를 통해
      추출해야 합니다. (예: 상태가 +1로 '변경'되는 순간 = 진입 이벤트)
"""

import numpy as np
import pandas as pd


def state_to_events(state: pd.Series, entry_state: int = 1) -> pd.Series:
    """State 시계열에서 Event 시계열을 추출

    Args:
        state: +1, 0, -1 등의 상태 시계열
        entry_state: 진입으로 간주할 상태 값 (기본 1 = Long)

    Returns:
        +1: entry_state로 진입하는 순간 (Long Entry)
        -1: entry_state에서 벗어나는 순간 (Long Exit)
         0: 그 외
    """
    prev = state.shift(1).fillna(0)
    events = pd.Series(0, index=state.index, dtype=int)

    # Long Entry: 오늘 == entry_state, 어제 != entry_state
    events[(state == entry_state) & (prev != entry_state)] = 1

    # Long Exit: 오늘 != entry_state, 어제 == entry_state
    events[(state != entry_state) & (prev == entry_state)] = -1

    return events


def golden_cross(prices: pd.Series, short: int = 5, long: int = 20) -> pd.Series:
    """이동평균선 골든크로스/데드크로스 상태

    +1: 단기 MA > 장기 MA (골든크로스 구간)
    -1: 단기 MA < 장기 MA (데드크로스 구간)
     0: 그 외 (없음)
    """
    ma_short = prices.rolling(window=short).mean()
    ma_long = prices.rolling(window=long).mean()

    signal = pd.Series(0, index=prices.index, dtype=int)
    signal[ma_short > ma_long] = 1
    signal[ma_short < ma_long] = -1
    return signal


def rsi_signal(
    prices: pd.Series, period: int = 14, oversold: float = 30, overbought: float = 70
) -> pd.Series:
    """RSI 과매수/과매도 상태

    +1: RSI <= oversold (과매도 구간)
    -1: RSI >= overbought (과매수 구간)
     0: 그 외
    """
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    signal = pd.Series(0, index=prices.index, dtype=int)
    signal[rsi <= oversold] = 1
    signal[rsi >= overbought] = -1
    return signal


def momentum_breakout(prices: pd.Series, lookback: int = 20) -> pd.Series:
    """모멘텀 돌파 상태

    +1: 당일 종가가 과거 N일 최고가를 돌파한 구간
    -1: 당일 종가가 과거 N일 최저가를 하향 돌파한 구간
     0: 그 외
    """
    highest = prices.rolling(window=lookback).max().shift(1)
    lowest = prices.rolling(window=lookback).min().shift(1)

    signal = pd.Series(0, index=prices.index, dtype=int)
    signal[prices > highest] = 1
    signal[prices < lowest] = -1
    return signal


def bollinger_signal(prices: pd.Series, period: int = 20, std: float = 2.0) -> pd.Series:
    """볼린저 밴드 반전 상태

    +1: 종가가 하단선 이하 → 반등 구간
    -1: 종가가 상단선 이상 → 하락 구간
     0: 그 외
    """
    ma = prices.rolling(window=period).mean()
    sigma = prices.rolling(window=period).std(ddof=0)

    upper = ma + std * sigma
    lower = ma - std * sigma

    signal = pd.Series(0, index=prices.index, dtype=int)
    signal[prices <= lower] = 1
    signal[prices >= upper] = -1
    return signal


def get_signal(name: str, prices: pd.Series, **kwargs) -> pd.Series:
    """문자열 이름으로 신호(상태) 함수 호출"""
    mapping = {
        "golden_cross": golden_cross,
        "rsi": rsi_signal,
        "momentum_breakout": momentum_breakout,
        "bollinger": bollinger_signal,
    }
    fn = mapping.get(name)
    if fn is None:
        raise ValueError(f"Unknown signal: {name}")
    return fn(prices, **kwargs)
