"""Parse Lean algorithm JSON results and compute metrics."""

import json
import math
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from scipy.optimize import minimize_scalar


def load_results(path: str) -> dict[str, Any]:
    """Load a Lean results JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _nav_series(nav_history: list[dict]) -> pd.Series:
    """Convert nav_history list to a pandas Series indexed by date."""
    df = pd.DataFrame(nav_history)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df["nav"]


def compute_metrics(nav_history: list[dict], risk_free: float = 0.02) -> dict[str, float]:
    """Compute CAGR, MDD, Sharpe, total return, volatility from nav_history."""
    nav = _nav_series(nav_history)
    if len(nav) < 2:
        return {
            "cagr": 0.0,
            "mdd": 0.0,
            "sharpe": 0.0,
            "total_return": 0.0,
            "volatility": 0.0,
        }

    total_ret = float(nav.iloc[-1] / nav.iloc[0] - 1)

    years = (nav.index[-1] - nav.index[0]).days / 365.25
    cagr = float((nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1) if years > 0 else 0.0

    returns = nav.pct_change().dropna()
    vol = float(returns.std(ddof=1) * np.sqrt(252)) if not returns.empty else 0.0

    if returns.empty:
        sharpe = 0.0
    else:
        excess = returns.mean() * 252 - risk_free
        vol_ddof = returns.std(ddof=1) * np.sqrt(252)
        sharpe = float(excess / vol_ddof) if vol_ddof != 0 else 0.0

    cummax = nav.cummax()
    mdd = float(((nav - cummax) / cummax).min())

    return {
        "cagr": cagr,
        "mdd": mdd,
        "sharpe": sharpe,
        "total_return": total_ret,
        "volatility": vol,
    }


def summarize_trades(trade_log: list[dict]) -> dict[str, float]:
    """Summarize trade_log into win_rate, avg_win, avg_loss, profit_factor."""
    if not trade_log:
        return {
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
            "n_trades": 0,
        }

    returns = pd.Series([t.get("trade_return", 0.0) for t in trade_log]).dropna()
    if returns.empty:
        return {
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
            "n_trades": 0,
        }

    wins = returns[returns > 0]
    losses = returns[returns <= 0]

    win_rate = float((returns > 0).mean())
    avg_win = float(wins.mean()) if len(wins) > 0 else 0.0
    avg_loss = float(losses.abs().mean()) if len(losses) > 0 else 0.0

    total_wins = wins.sum()
    total_losses = losses.abs().sum()
    if total_losses == 0:
        profit_factor = float("inf") if total_wins > 0 else 0.0
    else:
        profit_factor = float(total_wins / total_losses)

    return {
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "n_trades": len(returns),
    }


def compute_kelly_metrics(trade_log: list[dict]) -> dict[str, float]:
    """Numerical Kelly 및 수익률 통계를 계산"""
    returns = np.array([t.get("trade_return", 0.0) for t in trade_log])
    returns = returns[np.isfinite(returns)]
    n = len(returns)

    if n < 2:
        return {
            "f_star_numerical": 0.0,
            "f_star_normal_approx": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "skewness": 0.0,
            "kurtosis": 0.0,
            "valid": False,
        }

    min_ret = returns.min()
    if min_ret < 0:
        safe_upper = min(10.0, 0.999 / abs(min_ret))
    else:
        safe_upper = 10.0

    def objective(f):
        val = 1 + f * returns
        if np.any(val <= 0):
            return 1e10
        return -np.mean(np.log(val))

    result = minimize_scalar(objective, bounds=(0.0, safe_upper), method="bounded")
    f_star_numerical = float(result.x)

    mu = float(np.mean(returns))
    sigma2 = float(np.var(returns, ddof=0))
    f_star_normal_approx = max(0.0, mu / sigma2) if sigma2 != 0 else 0.0

    return {
        "f_star_numerical": f_star_numerical,
        "f_star_normal_approx": f_star_normal_approx,
        "mean": mu,
        "median": float(np.median(returns)),
        "std": float(np.std(returns, ddof=1)),
        "skewness": float(scipy_stats.skew(returns, bias=False)),
        "kurtosis": float(scipy_stats.kurtosis(returns, bias=False)),
        "valid": True,
    }


def simulate_nav_for_fractions(
    trade_log: list[dict],
    price_history: list[dict],
    initial_cash: float,
    direction: str = "long",
    fractions: list[float] | None = None,
) -> dict[str, pd.Series]:
    """trade_log와 price_history를 기반으로 여러 Kelly fraction의 일별 NAV를 시뮬레이션"""
    if fractions is None:
        fractions = [0.0, 0.25, 0.5, 1.0, 1.4]
    if not price_history or not trade_log:
        return {}

    price_df = pd.DataFrame(price_history)
    price_df["date"] = pd.to_datetime(price_df["date"])
    price_df = price_df.set_index("date").sort_index()

    entries_by_date: dict[str, list[dict]] = {}
    exits_by_date: dict[str, list[dict]] = {}
    for trade in trade_log:
        ed = trade.get("entry_date")
        ex = trade.get("exit_date")
        if ed:
            entries_by_date.setdefault(ed, []).append(trade)
        if ex:
            exits_by_date.setdefault(ex, []).append(trade)

    COST_RATE = 0.002  # commission + slippage

    results: dict[str, pd.Series] = {}
    for f in fractions:
        cash = float(initial_cash)
        shares = 0.0
        navs = []
        for date in price_df.index:
            date_str = str(date.date())
            price = float(price_df.loc[date, "price"])

            # Process exits first
            if date_str in exits_by_date:
                for trade in exits_by_date[date_str]:
                    if shares == 0:
                        continue
                    exit_price = float(trade.get("exit_price", 0.0))
                    if exit_price <= 0:
                        continue
                    exit_cost = abs(shares) * exit_price * COST_RATE
                    if direction == "long":
                        cash += shares * exit_price - exit_cost
                    else:
                        entry_price = float(trade.get("entry_price", 0.0))
                        cash += abs(shares) * (entry_price - exit_price) - exit_cost
                    shares = 0.0

            # Process entries
            if date_str in entries_by_date:
                for trade in entries_by_date[date_str]:
                    entry_price = float(trade.get("entry_price", 0.0))
                    if entry_price <= 0 or cash <= 0:
                        continue
                    investment = cash * f
                    entry_cost = investment * COST_RATE
                    if direction == "long":
                        shares = investment / entry_price
                        cash -= investment + entry_cost
                    else:
                        shares = -investment / entry_price
                        cash += investment - entry_cost

            nav = cash + shares * price
            navs.append(nav)

        label = f"{f*100:.0f}% Kelly" if f > 0 else "Cash (f=0)"
        results[label] = pd.Series(navs, index=price_df.index)

    return results


def kelly_curve_data(trade_log: list[dict], n_points: int = 200, max_f: float = 5.0):
    """f에 따른 E[log(1+fX)] 데이터를 반환"""
    returns = np.array([t.get("trade_return", 0.0) for t in trade_log])
    returns = returns[np.isfinite(returns)]
    if len(returns) < 2:
        return np.array([]), np.array([])

    min_ret = returns.min()
    if min_ret < 0:
        safe_max_f = min(max_f, 0.999 / abs(min_ret))
    else:
        safe_max_f = max_f

    f_vals = np.linspace(0, safe_max_f, n_points)
    exp_log = []
    for f in f_vals:
        val = 1 + f * returns
        if np.any(val <= 0):
            exp_log.append(np.nan)
        else:
            exp_log.append(np.mean(np.log(val)))
    return f_vals, np.array(exp_log)
