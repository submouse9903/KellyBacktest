"""이벤트 기반 신호 드리븐 백테스팅 엔진

핵심 원칙:
- 입력 signals는 이벤트(Event) 시계열입니다: +1(진입), -1(청산), 0(무이벤트)
- 모든 거래는 T일 이벤트 발생 → T+1일 실행(Next-Day Execution)
- 동일 방향 이벤트가 보유 중 발생하면 보유 기간을 연장(Renewal)합니다.
"""

import numpy as np
import pandas as pd

from config import COMMISSION_RATE, SLIPPAGE_RATE


def _apply_costs(trade_value: float) -> float:
    """거래비용 적용"""
    return abs(trade_value) * (COMMISSION_RATE + SLIPPAGE_RATE)


def run_strategy(
    prices: pd.Series,
    signals: pd.Series,
    kelly_fraction: float,
    holding_period: int = 20,
    initial_cash: float = 1_000_000,
    direction: str = "long",
    exit_on_opposite: bool = True,
    allow_renewal: bool = True,
) -> dict:
    """이벤트 기반 켈리 백테스팅

    Args:
        prices: 종가 시계열
        signals: 이벤트 시계열 (+1=진입, -1=청산, 0=무이벤트)
        kelly_fraction: 각 진입 시 베팅할 자본 비중
        holding_period: 최대 보유 기간 (거래일, 진입 실행일 기준)
        initial_cash: 초기 자본금
        direction: 'long' 또는 'short'
        exit_on_opposite: 청산 이벤트 발생 시 조기 청산 여부
        allow_renewal: 동일 방향 이벤트 발생 시 보유 기간 연장

    Returns:
        {
            "nav": pd.Series,
            "buyhold": pd.Series,
            "trade_log": pd.DataFrame,
            "position": pd.Series,
        }
    """
    prices = prices.dropna().sort_index()
    signals = signals.reindex(prices.index).fillna(0).astype(int)

    entry_signal = 1 if direction == "long" else -1
    exit_signal = -1 if direction == "long" else 1

    cash = float(initial_cash)
    shares = 0.0
    nav = pd.Series(index=prices.index, dtype=float)
    position = pd.Series(0.0, index=prices.index)
    trades = []
    active_trade = None

    entry_dates = signals[signals == entry_signal].index

    for i, date in enumerate(prices.index):
        price = prices.iloc[i]

        # ------------------------------------------------------------------
        # 1) Renewal: 동일 방향 이벤트가 발생하여 오늘 새 진입이 예정되어 있으면
        #    기존 포지션의 보유 기간을 연장
        # ------------------------------------------------------------------
        if allow_renewal and active_trade is not None and i > 0:
            prev_date = prices.index[i - 1]
            if prev_date in entry_dates:
                active_trade["target_exit_idx"] = min(i + holding_period, len(prices) - 1)

        # ------------------------------------------------------------------
        # 2) 활성 거래 청산 조건 체크
        # ------------------------------------------------------------------
        if active_trade is not None:
            should_exit = False
            exit_reason = ""

            # a) 최대 보유 기간 도달
            if i >= active_trade["target_exit_idx"]:
                should_exit = True
                exit_reason = "holding_period"
            # b) 반대 신호 조기 청산 (Next-Day: 어제 exit event → 오늘 청산)
            elif exit_on_opposite and i > 0 and signals.iloc[i - 1] == exit_signal:
                should_exit = True
                exit_reason = "opposite_signal"
            # c) 데이터 끝
            elif i == len(prices) - 1:
                should_exit = True
                exit_reason = "end_of_data"

            if should_exit:
                exit_price = price
                trade_value = active_trade["shares"] * exit_price
                cost = _apply_costs(trade_value)
                cash += trade_value - cost
                trade_return = (exit_price - active_trade["entry_price"]) / active_trade["entry_price"]
                if direction == "short":
                    trade_return = -trade_return

                trades.append(
                    {
                        "entry_date": prices.index[active_trade["entry_idx"]],
                        "exit_date": date,
                        "entry_price": active_trade["entry_price"],
                        "exit_price": exit_price,
                        "shares": active_trade["shares"],
                        "kelly_fraction": active_trade["kelly_fraction"],
                        "exit_reason": exit_reason,
                        "trade_return": trade_return,
                        "cash_after": cash,
                    }
                )
                shares = 0.0
                active_trade = None

        # ------------------------------------------------------------------
        # 3) 새 진입 (Next-Day: 어제 entry event → 오늘 진입)
        # ------------------------------------------------------------------
        if active_trade is None and i > 0:
            prev_date = prices.index[i - 1]
            if prev_date in entry_dates and kelly_fraction > 0:
                entry_price = price
                investment = cash * kelly_fraction
                if investment > 0 and entry_price > 0:
                    new_shares = investment / entry_price
                    cost = _apply_costs(investment)
                    cash -= investment + cost
                    shares = new_shares
                    active_trade = {
                        "entry_idx": i,
                        "entry_price": entry_price,
                        "shares": shares,
                        "target_exit_idx": min(i + holding_period, len(prices) - 1),
                        "kelly_fraction": kelly_fraction,
                    }

        # ------------------------------------------------------------------
        # 4) 일별 NAV 계산
        # ------------------------------------------------------------------
        nav.loc[date] = cash + shares * price
        if nav.loc[date] > 0 and shares > 0:
            position.loc[date] = (shares * price) / nav.loc[date]
        else:
            position.loc[date] = 0.0

    # Buy & Hold 벤치마크 (첫 번째 이벤트 다음날 또는 전체 기간의 첫날에 100% 투자)
    if len(entry_dates) > 0:
        first_entry_loc = prices.index.get_loc(entry_dates[0]) + 1
        first_entry_loc = min(first_entry_loc, len(prices) - 1)
    else:
        first_entry_loc = 0

    shares_bh = initial_cash / prices.iloc[first_entry_loc]
    buyhold = pd.Series(index=prices.index, dtype=float)
    for j, d in enumerate(prices.index):
        if j < first_entry_loc:
            buyhold.loc[d] = initial_cash
        else:
            buyhold.loc[d] = shares_bh * prices.iloc[j]

    return {
        "nav": nav,
        "buyhold": buyhold,
        "trade_log": pd.DataFrame(trades),
        "position": position,
    }
