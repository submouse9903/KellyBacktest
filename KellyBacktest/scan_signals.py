"""여러 종목/전략에 대해 자동으로 켈리 분석 및 Grid Search를 실행하는 CLI 스캐너"""

import pandas as pd

from src import db_connector, signal_engine, strategy_analyzer


def main():
    symbols = ["005930", "000660", "035420", "005490"]
    strategies = {
        "golden_cross": {
            "fn": signal_engine.golden_cross,
            "param_grid": {"short": [3, 5, 10], "long": [20, 30, 60]},
        },
        "rsi": {
            "fn": signal_engine.rsi_signal,
            "param_grid": {"period": [10, 14, 21], "oversold": [25, 30], "overbought": [70, 75]},
        },
        "momentum_breakout": {
            "fn": signal_engine.momentum_breakout,
            "param_grid": {"lookback": [10, 20, 40]},
        },
        "bollinger": {
            "fn": signal_engine.bollinger_signal,
            "param_grid": {"period": [10, 20, 30], "std": [1.5, 2.0, 2.5]},
        },
    }
    holding_periods = [10, 20, 40]
    direction = "long"

    print("=" * 80)
    print("Signal-Driven Kelly Scanner (Event-based + Adjusted Kelly)")
    print("=" * 80)

    for sym in symbols:
        print(f"\n>>> 종목: {sym}")
        try:
            prices = db_connector.get_prices_from_db([sym], start_date="2020-01-02")
            if prices.empty or sym not in prices.columns:
                print(f"  [SKIP] 데이터 없음")
                continue
            prices = prices[sym].dropna()
        except Exception as e:
            print(f"  [ERROR] DB 조회 실패: {e}")
            continue

        for name, config in strategies.items():
            print(f"\n  -- 전략: {name}")
            grid_df = strategy_analyzer.grid_search(
                prices,
                signal_name=name,
                param_grid=config["param_grid"],
                holding_periods=holding_periods,
                direction=direction,
                min_trades=20,
                min_f_star=0.0,
                exit_on_opposite=True,
                allow_renewal=True,
            )

            if grid_df.empty:
                print(f"     [결과] 양수 켈리 조합 없음")
            else:
                top = grid_df.iloc[0]
                params = {k: top[k] for k in config["param_grid"].keys()}
                print(
                    f"     [BEST] f*={top['f_star_adjusted']*100:.1f}% | "
                    f"Win={top['win_rate']*100:.1f}% | Trades={top['n_trades']} | "
                    f"Params={params} | HP={top['holding_period']}"
                )
                # 상위 3개 출력
                for idx, row in grid_df.head(3).iterrows():
                    p = {k: row[k] for k in config["param_grid"].keys()}
                    print(
                        f"       #{idx+1} f*={row['f_star_adjusted']*100:.1f}% | "
                        f"Win={row['win_rate']*100:.1f}% | Trades={row['n_trades']} | "
                        f"Params={p} | HP={row['holding_period']}"
                    )


if __name__ == "__main__":
    main()
