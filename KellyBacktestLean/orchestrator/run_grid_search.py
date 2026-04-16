"""Grid Search orchestrator for KellyBacktestLean.

Uses Pandas for fast In-Sample Kelly analysis, then runs Lean Docker backtests
only for parameter combinations that meet min_trades and positive f_star_adjusted.
"""

import itertools
import json
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

# Allow importing from KellyBacktest/src
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
KELLYBACKTEST_SRC = PROJECT_ROOT / "KellyBacktest" / "src"
if str(KELLYBACKTEST_SRC) not in sys.path:
    sys.path.insert(0, str(KELLYBACKTEST_SRC))

from signal_engine import get_signal, state_to_events
from strategy_analyzer import extract_signal_returns, compute_kelly_params
from data_loader import load_csv, validate_data

from run_single_backtest import run_single_backtest

# Paths
ORCHESTRATOR_DIR = Path(__file__).parent.resolve()
LEAN_DIR = ORCHESTRATOR_DIR.parent
RESULTS_DIR = LEAN_DIR / "results"
DATA_DIR = LEAN_DIR / "data"


def load_prices(ticker: str, data_dir: Path = DATA_DIR) -> pd.Series:
    """Load price data for a ticker.

    Priority:
      1. CSV file named {ticker}.csv in data_dir (wide-form expected).
      2. Fallback to KellyBacktest DB connector.
    """
    csv_path = data_dir / "equity" / "usa" / "daily" / f"{ticker.lower()}.csv"
    if csv_path.exists():
        prices = load_csv(csv_path, wide_form=True)
        if isinstance(prices, pd.DataFrame):
            if ticker in prices.columns:
                prices = prices[ticker]
            else:
                prices = prices.iloc[:, 0]
        return validate_data(prices)

    # Fallback: try existing DB connector
    try:
        import db_connector
        df = db_connector.get_prices_from_db([ticker])
        if not df.empty:
            prices = df[ticker] if ticker in df.columns else df.iloc[:, 0]
            return validate_data(prices)
    except Exception:
        pass

    raise FileNotFoundError(
        f"No local CSV ({csv_path}) and no DB data found for ticker {ticker}."
    )


def run_grid_search(
    ticker: str,
    signal_name: str,
    param_grid: dict,
    holding_periods: list[int],
    direction: str = "long",
    min_trades: int = 30,
    min_f_star: float = 0.0,
    exit_on_opposite: bool = True,
    allow_renewal: bool = True,
    initial_cash: float = 1_000_000,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    run_lean: bool = True,
    verbose: bool = True,
) -> pd.DataFrame:
    """Run grid search: Pandas IS filtering + optional Lean backtests.

    Args:
        ticker: Ticker symbol.
        signal_name: Name of the signal (e.g. 'golden_cross').
        param_grid: Dict of parameter name -> list of candidate values.
        holding_periods: List of holding periods to test.
        direction: 'long' or 'short'.
        min_trades: Minimum number of trades to accept a combo.
        min_f_star: Minimum f_star_adjusted threshold.
        exit_on_opposite: Whether to exit on opposite signal.
        allow_renewal: Whether to allow holding-period renewal.
        initial_cash: Starting cash for Lean backtests.
        start_date: Optional start date string to slice prices.
        end_date: Optional end date string to slice prices.
        run_lean: If True, run Lean Docker for qualifying combos.
        verbose: Print progress.

    Returns:
        DataFrame with columns:
          signal, direction, holding_period, <params>, n_trades, win_rate,
          avg_win, avg_loss, f_star_adjusted, final_nav, cagr, mdd
    """
    prices = load_prices(ticker)
    if start_date:
        prices = prices[prices.index >= pd.to_datetime(start_date)]
    if end_date:
        prices = prices[prices.index <= pd.to_datetime(end_date)]

    prices = prices.dropna().sort_index()
    if len(prices) < max(holding_periods, default=20) * 2:
        raise ValueError("Insufficient price data for the requested holding periods.")

    keys = list(param_grid.keys())
    values = list(param_grid.values())
    results = []

    entry_state = 1 if direction == "long" else -1

    for combo in itertools.product(*values):
        kwargs = dict(zip(keys, combo))
        state = get_signal(signal_name, prices, **kwargs)
        events = state_to_events(state, entry_state=entry_state)

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

            if not stats["valid"]:
                continue
            if stats["n_trades"] < min_trades:
                continue
            if stats["f_star_adjusted"] < min_f_star:
                continue

            row = {
                "signal": signal_name,
                "direction": direction,
                "holding_period": hp,
                **kwargs,
                "n_trades": stats["n_trades"],
                "win_rate": stats["win_rate"],
                "avg_win": stats["avg_win"],
                "avg_loss": stats["avg_loss"],
                "f_star_adjusted": stats["f_star_adjusted"],
            }

            # Run Lean only for positive f_star_adjusted
            if run_lean and stats["f_star_adjusted"] > 0:
                config = {
                    "symbol": ticker,
                    "start_date": str(prices.index[0].date()),
                    "end_date": str(prices.index[-1].date()),
                    "signal_name": signal_name,
                    "holding_period": hp,
                    "direction": direction,
                    "exit_on_opposite": exit_on_opposite,
                    "allow_renewal": allow_renewal,
                    "kelly_fraction": float(stats["f_star_adjusted"]),
                    "initial_cash": initial_cash,
                    **kwargs,
                }
                try:
                    lean_result = run_single_backtest(config, verbose=verbose)
                    row["final_nav"] = lean_result.get("final_nav")
                    row["cagr"] = lean_result.get("cagr")
                    row["mdd"] = lean_result.get("mdd")
                except Exception as exc:
                    if verbose:
                        print(f"  Lean backtest failed for {kwargs}, hp={hp}: {exc}")
                    row["final_nav"] = None
                    row["cagr"] = None
                    row["mdd"] = None
            else:
                row["final_nav"] = None
                row["cagr"] = None
                row["mdd"] = None

            results.append(row)

    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values("f_star_adjusted", ascending=False).reset_index(drop=True)
    return df


def main():
    """Example: Golden Cross grid search on 005930."""
    ticker = "005930"
    signal_name = "golden_cross"
    param_grid = {
        "short": [5, 10, 15],
        "long": [20, 30, 60],
    }
    holding_periods = [10, 20, 40]

    print(f"Running grid search for {ticker} | signal={signal_name}")
    df = run_grid_search(
        ticker=ticker,
        signal_name=signal_name,
        param_grid=param_grid,
        holding_periods=holding_periods,
        direction="long",
        min_trades=20,
        min_f_star=0.0,
        run_lean=False,  # Set to True when Docker + Lean algo are ready
        verbose=True,
    )

    if df.empty:
        print("No qualifying parameter combinations found.")
        return

    csv_path = RESULTS_DIR / "grid_search_results.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"Saved grid search results to {csv_path}")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
