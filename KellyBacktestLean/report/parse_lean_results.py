"""Parse Lean algorithm JSON results and compute metrics."""

import json
import math
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd


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
