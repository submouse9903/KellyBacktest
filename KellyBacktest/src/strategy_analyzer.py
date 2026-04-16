"""전략 이벤트의 통계적 성과 분석 및 켈리 파라미터 계산

핵심 원칙:
- signal_engine은 '상태(State)'를 반환합니다.
- 이 모듈은 상태를 '이벤트(Event)'로 변환하고, 이벤트 기반으로 거래 수익률을 추출합니다.
- 모든 거래는 T일 이벤트 발생 → T+1일 실행(Next-Day Execution) 원칙을 따릅니다.
"""

import itertools
from typing import Optional

import pandas as pd

from src import signal_engine


def state_to_events(state: pd.Series, entry_state: int = 1) -> pd.Series:
    """State 시계열에서 Event 시계열을 추출

    +1: entry_state로 진입하는 순간 (Long Entry)
    -1: entry_state에서 벗어나는 순간 (Long Exit)
     0: 그 외
    """
    return signal_engine.state_to_events(state, entry_state=entry_state)


def extract_signal_returns(
    prices: pd.Series,
    events: pd.Series,
    holding_period: int = 20,
    direction: str = "long",
    exit_on_opposite: bool = True,
    allow_renewal: bool = True,
) -> pd.Series:
    """이벤트 발생 시 진입 → Next-Day 실행 가정으로 거래별 수익률 추출

    Args:
        prices: 종가 시계열
        events: +1(진입 이벤트), -1(청산 이벤트), 0(무이벤트)
        holding_period: 최대 보유 기간 (거래일, 진입 실행일 기준)
        direction: 'long' 또는 'short'
        exit_on_opposite: 청산 이벤트 발생 시 조기 청산 여부
        allow_renewal: 동일 진입 이벤트 발생 시 보유 기간 연장 여부

    Returns:
        각 거래별 수익률 시리즈
    """
    prices = prices.dropna().sort_index()
    events = events.reindex(prices.index).fillna(0).astype(int)

    entry_event = 1 if direction == "long" else -1
    exit_event = -1 if direction == "long" else 1

    trade_returns = []

    entry_dates = events[events == entry_event].index

    for entry_date in entry_dates:
        entry_idx = prices.index.get_loc(entry_date)
        # Next-Day execution: 이벤트 발생 다음 거래일에 진입
        entry_idx += 1
        if entry_idx >= len(prices):
            continue

        entry_price = prices.iloc[entry_idx]

        # 기본 청산일: holding_period 후
        max_exit_idx = min(entry_idx + holding_period, len(prices) - 1)
        exit_idx = max_exit_idx

        if exit_on_opposite or allow_renewal:
            future_events = events.iloc[entry_idx : max_exit_idx + 1]

            if exit_on_opposite:
                opposite_mask = future_events == exit_event
                if opposite_mask.any():
                    first_opposite_idx = opposite_mask[opposite_mask].index[0]
                    opposite_loc = prices.index.get_loc(first_opposite_idx)
                    exit_idx = min(opposite_loc + 1, len(prices) - 1)

            if allow_renewal:
                # 동일 방향 이벤트가 있으면 보유 기간 연장
                # 단, 이미 결정된 exit_idx보다 늦은 이벤트 중 마지막 것까지
                renew_mask = future_events == entry_event
                if renew_mask.any():
                    # renew 이벤트 중 exit_idx를 넘어서는 것이 있으면 연장
                    renew_dates = renew_mask[renew_mask].index
                    for rd in renew_dates:
                        renew_loc = prices.index.get_loc(rd)
                        new_exit = min(renew_loc + 1 + holding_period, len(prices) - 1)
                        if new_exit > exit_idx:
                            exit_idx = new_exit

        exit_price = prices.iloc[exit_idx]
        ret = (exit_price - entry_price) / entry_price

        if direction == "short":
            ret = -ret

        trade_returns.append(ret)

    return pd.Series(trade_returns, name="trade_return")


def compute_kelly_params(returns: pd.Series, min_trades: int = 10) -> dict:
    """거래 수익률로부터 켈리 파라미터 계산

    핵심 지표는 Numerical Kelly (E[log(1+fX)] 최적화)입니다.
    f_star_adjusted 및 f_star는 레거시 참고용으로 유지됩니다.
    """
    from src import kelly_engine

    returns = returns.dropna()
    n = len(returns)

    if n < min_trades:
        return {
            "n_trades": n,
            "win_rate": 0.0,
            "loss_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "f_star": 0.0,
            "f_star_adjusted": 0.0,
            "f_star_numerical": 0.0,
            "f_star_normal_approx": 0.0,
            "return_stats": {
                "mean": 0.0,
                "median": 0.0,
                "std": 0.0,
                "skewness": 0.0,
                "kurtosis": 0.0,
            },
            "valid": False,
        }

    wins = returns[returns > 0]
    losses = returns[returns <= 0]

    p = len(wins) / n if n > 0 else 0.0
    q = 1 - p
    b = float(wins.mean()) if len(wins) > 0 else 0.0
    avg_loss = float(losses.abs().mean()) if len(losses) > 0 else 0.0

    # 고전 이산 켈리 (손실률 = 100% 가정) - 참고용
    f_star = 0.0
    if b > 0:
        f_star = (b * p - q) / b

    # 현대 수정 켈리 (평균 손실 크기 반영) - 참고용
    f_star_adjusted = 0.0
    if b > 0 and avg_loss > 0:
        f_star_adjusted = (b * p - avg_loss * q) / (b * avg_loss)

    # Numerical Kelly (핵심)
    f_star_numerical = kelly_engine.numerical_kelly(returns.values)
    f_star_normal_approx = kelly_engine.normal_approx_kelly(returns.values)
    ret_stats = kelly_engine.return_stats(returns.values)

    return {
        "n_trades": n,
        "win_rate": p,
        "loss_rate": q,
        "avg_win": b,
        "avg_loss": avg_loss,
        "f_star": f_star,
        "f_star_adjusted": f_star_adjusted,
        "f_star_numerical": f_star_numerical,
        "f_star_normal_approx": f_star_normal_approx,
        "return_stats": ret_stats,
        "valid": True,
    }


def grid_search(
    prices: pd.Series,
    signal_name: str,
    param_grid: dict,
    holding_periods: list[int],
    direction: str = "long",
    min_trades: int = 30,
    min_f_star: float = 0.0,
    exit_on_opposite: bool = True,
    allow_renewal: bool = True,
) -> pd.DataFrame:
    """전략 파라미터 조합을 자동으로 탐색하여 켈리 비중이 양수인 조합을 찾음

    Args:
        prices: 종가 시계열
        signal_name: signal_engine.get_signal()에 전달할 이름
        param_grid: {파라미터명: [후보값 리스트]}
        holding_periods: 테스트할 보유 기간 리스트
        direction: 'long' 또는 'short'
        min_trades: 최소 거래 횟수 필터
        min_f_star: 최소 켈리 비중 필터
        exit_on_opposite: 청산 이벤트 시 조기 청산
        allow_renewal: 보유 기간 연장 허용

    Returns:
        각 조합별 결과 DataFrame (f_star_adjusted 내림차순 정렬)
    """
    prices = prices.dropna().sort_index()
    keys = list(param_grid.keys())
    values = list(param_grid.values())

    results = []

    for combo in itertools.product(*values):
        kwargs = dict(zip(keys, combo))
        state = signal_engine.get_signal(signal_name, prices, **kwargs)
        events = state_to_events(state, entry_state=1 if direction == "long" else -1)

        for hp in holding_periods:
            returns = extract_signal_returns(
                prices,
                events,
                holding_period=hp,
                direction=direction,
                exit_on_opposite=exit_on_opposite,
                allow_renewal=allow_renewal,
            )
            stats = compute_kelly_params(returns, min_trades=min_trades)

            if stats["valid"] and stats["n_trades"] >= min_trades and stats["f_star_numerical"] >= min_f_star:
                row = {
                    "signal": signal_name,
                    "direction": direction,
                    "holding_period": hp,
                    **kwargs,
                    "n_trades": stats["n_trades"],
                    "win_rate": stats["win_rate"],
                    "avg_win": stats["avg_win"],
                    "avg_loss": stats["avg_loss"],
                    "f_star_numerical": stats["f_star_numerical"],
                    "f_star_normal_approx": stats["f_star_normal_approx"],
                    "f_star_adjusted": stats["f_star_adjusted"],
                    "f_star": stats["f_star"],
                }
                results.append(row)

    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values("f_star_numerical", ascending=False).reset_index(drop=True)
    return df


def analyze_with_oos(
    prices: pd.Series,
    events: pd.Series,
    split_ratio: float = 0.7,
    holding_period: int = 20,
    direction: str = "long",
    exit_on_opposite: bool = True,
    allow_renewal: bool = True,
) -> tuple[dict, float, pd.Series]:
    """In-Sample으로 켈리 파라미터를 추정하고, Out-of-Sample으로 거래 수익률을 추출

    Returns:
        (is_stats, f_star, oos_returns)
    """
    prices = prices.dropna().sort_index()
    events = events.reindex(prices.index).fillna(0).astype(int)

    split_idx = int(len(prices) * split_ratio)
    if split_idx < 50 or split_idx > len(prices) - 50:
        # 데이터가 너무 짧으면 OOS 없이 전체 분석
        returns = extract_signal_returns(
            prices, events, holding_period, direction, exit_on_opposite, allow_renewal
        )
        stats = compute_kelly_params(returns)
        f_star = max(0.0, stats.get("f_star_adjusted", 0.0))
        return stats, f_star, returns

    is_prices = prices.iloc[:split_idx]
    is_events = events.iloc[:split_idx]
    oos_prices = prices.iloc[split_idx:]
    oos_events = events.iloc[split_idx:]

    # IS에서 f* 추정
    is_returns = extract_signal_returns(
        is_prices, is_events, holding_period, direction, exit_on_opposite, allow_renewal
    )
    is_stats = compute_kelly_params(is_returns)
    f_star = max(0.0, is_stats.get("f_star_numerical", 0.0))

    # OOS에서 동일 f*로 거래 수익률 추출 (백테스트는 별도 엔진에서)
    oos_returns = extract_signal_returns(
        oos_prices, oos_events, holding_period, direction, exit_on_opposite, allow_renewal
    )

    return is_stats, f_star, oos_returns
