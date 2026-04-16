"""Out-of-Sample (OOS) workflow orchestrator for KellyBacktestLean.

1. Load price data (Pandas).
2. Split into IS / OOS by date (default 70 / 30).
3. Compute In-Sample signals, trade returns, and Kelly parameters.
4. Run a Lean Docker backtest on the OOS period using the IS-derived Kelly fraction.
5. Compare IS statistics vs OOS Lean results and save a summary JSON.
"""

import json
import sys
from pathlib import Path

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


def split_is_oos(prices: pd.Series, split_ratio: float = 0.7) -> tuple[pd.Series, pd.Series]:
    """Split prices into IS and OOS by date."""
    prices = prices.dropna().sort_index()
    split_idx = int(len(prices) * split_ratio)
    if split_idx < 50 or split_idx > len(prices) - 50:
        raise ValueError(
            f"Cannot split series of length {len(prices)} with ratio {split_ratio}."
        )
    is_prices = prices.iloc[:split_idx]
    oos_prices = prices.iloc[split_idx:]
    return is_prices, oos_prices


def run_oos(
    ticker: str,
    signal_name: str,
    signal_params: dict,
    holding_period: int = 20,
    direction: str = "long",
    split_ratio: float = 0.7,
    exit_on_opposite: bool = True,
    allow_renewal: bool = True,
    initial_cash: float = 1_000_000,
    min_trades: int = 10,
    verbose: bool = True,
) -> dict:
    """Run the full OOS workflow.

    Returns:
        Summary dict containing:
          - ticker, signal_name, signal_params, holding_period, direction
          - split_ratio, is_start, is_end, oos_start, oos_end
          - is_stats: Kelly parameters from IS trades
          - kelly_fraction: max(0, f_star_adjusted) used for OOS Lean backtest
          - oos_lean_result: Raw Lean backtest result dict
          - comparison: simple IS vs OOS comparison metrics
    """
    prices = load_prices(ticker)
    is_prices, oos_prices = split_is_oos(prices, split_ratio=split_ratio)

    entry_state = 1 if direction == "long" else -1

    # --- In-Sample analysis ---
    is_state = get_signal(signal_name, is_prices, **signal_params)
    is_events = state_to_events(is_state, entry_state=entry_state)
    is_returns = extract_signal_returns(
        is_prices,
        is_events,
        holding_period=holding_period,
        direction=direction,
        exit_on_opposite=exit_on_opposite,
        allow_renewal=allow_renewal,
    )
    is_stats = compute_kelly_params(is_returns, min_trades=min_trades)
    kelly_fraction = max(0.0, is_stats.get("f_star_adjusted", 0.0))

    if verbose:
        print(f"[OOS] IS period: {is_prices.index[0].date()} ~ {is_prices.index[-1].date()}")
        print(f"[OOS] IS trades: {is_stats['n_trades']}, f_star_adjusted: {is_stats['f_star_adjusted']:.4f}")
        print(f"[OOS] Kelly fraction for OOS: {kelly_fraction:.4f}")

    # --- OOS Lean backtest ---
    oos_config = {
        "symbol": ticker,
        "start_date": str(oos_prices.index[0].date()),
        "end_date": str(oos_prices.index[-1].date()),
        "signal_name": signal_name,
        "holding_period": holding_period,
        "direction": direction,
        "exit_on_opposite": exit_on_opposite,
        "allow_renewal": allow_renewal,
        "kelly_fraction": float(kelly_fraction),
        "initial_cash": initial_cash,
        **signal_params,
    }

    oos_lean_result = run_single_backtest(oos_config, verbose=verbose)

    # --- Comparison ---
    comparison = {
        "is_n_trades": is_stats["n_trades"],
        "is_win_rate": is_stats["win_rate"],
        "is_avg_win": is_stats["avg_win"],
        "is_avg_loss": is_stats["avg_loss"],
        "is_f_star_adjusted": is_stats["f_star_adjusted"],
        "oos_final_nav": oos_lean_result.get("final_nav"),
        "oos_cagr": oos_lean_result.get("cagr"),
        "oos_mdd": oos_lean_result.get("mdd"),
        "oos_total_return": oos_lean_result.get("total_return"),
    }

    summary = {
        "ticker": ticker,
        "signal_name": signal_name,
        "signal_params": signal_params,
        "holding_period": holding_period,
        "direction": direction,
        "split_ratio": split_ratio,
        "is_start": str(is_prices.index[0].date()),
        "is_end": str(is_prices.index[-1].date()),
        "oos_start": str(oos_prices.index[0].date()),
        "oos_end": str(oos_prices.index[-1].date()),
        "is_stats": is_stats,
        "kelly_fraction": kelly_fraction,
        "oos_lean_result": oos_lean_result,
        "comparison": comparison,
    }

    return summary


def main():
    """Runnable example for 005930 Golden Cross OOS."""
    ticker = "005930"
    signal_name = "golden_cross"
    signal_params = {"short": 5, "long": 20}
    holding_period = 20

    print(f"Running OOS workflow for {ticker} | signal={signal_name} | params={signal_params}")
    try:
        summary = run_oos(
            ticker=ticker,
            signal_name=signal_name,
            signal_params=signal_params,
            holding_period=holding_period,
            direction="long",
            split_ratio=0.7,
            exit_on_opposite=True,
            allow_renewal=True,
            initial_cash=1_000_000,
            min_trades=10,
            verbose=True,
        )
    except Exception as exc:
        print(f"OOS workflow failed: {exc}")
        sys.exit(1)

    summary_path = RESULTS_DIR / "oos_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nSaved OOS summary to {summary_path}")
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
