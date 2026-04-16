from AlgorithmImports import *
import json
import os
from datetime import datetime, timedelta

from lean_signals import get_signal
from lean_utils import CustomFeeModel, CustomSlippageModel, save_results


class KrxDailyData(PythonData):
    """Custom data source for KRX daily OHLCV CSV files.

    Expects CSV format: date,open,high,low,close,volume
    Date format: yyyy-MM-dd
    """

    def GetSource(self, config, date, isLiveMode):
        path = f"/Data/equity/usa/daily/{config.Symbol.Value.lower()}.csv"
        return SubscriptionDataSource(path, SubscriptionTransportMedium.LocalFile)

    def Reader(self, config, line, date, isLiveMode):
        if not line or line.strip() == "" or line.startswith("date"):
            return None

        parts = line.split(",")
        if len(parts) < 6:
            return None

        dt = datetime.strptime(parts[0].strip(), "%Y-%m-%d")
        # Daily bar is considered complete at market close.
        # We attach a dummy close time (06:30 UTC ≈ 15:30 KST)
        dt = dt + timedelta(hours=6, minutes=30)

        data = KrxDailyData()
        data.Symbol = config.Symbol
        data.Time = dt
        data.EndTime = dt
        data.Value = float(parts[4])
        data.Open = float(parts[1])
        data.High = float(parts[2])
        data.Low = float(parts[3])
        data.Close = float(parts[4])
        data.Volume = float(parts[5])
        return data


class KellySignalAlgorithm(QCAlgorithm):
    def Initialize(self):
        # Read config from the same directory
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "config.json"
        )
        with open(config_path, "r", encoding="utf-8-sig") as f:
            self.config = json.load(f)

        cfg = self.config

        # Dates and cash
        start = cfg.get("start_date", "2020-01-01").split("-")
        end = cfg.get("end_date", "2023-12-31").split("-")
        self.SetStartDate(int(start[0]), int(start[1]), int(start[2]))
        self.SetEndDate(int(end[0]), int(end[1]), int(end[2]))
        self.SetCash(float(cfg.get("initial_cash", 1_000_000)))

        # Symbol via custom data
        self.symbol = self.AddData(KrxDailyData, cfg["symbol"], Resolution.Daily).Symbol
        self.SetBrokerageModel(BrokerageName.Default, AccountType.Margin)

        # Transaction cost models
        self.Securities[self.symbol].SetFeeModel(CustomFeeModel(0.0015))
        self.Securities[self.symbol].SetSlippageModel(CustomSlippageModel(0.0005))

        # Strategy parameters
        self.signal_name = cfg.get("signal_name", "golden_cross")
        self.signal_params = cfg.get("signal_params", {})
        if not self.signal_params:
            # Orchestrator flattens params into top-level config keys
            if self.signal_name == "golden_cross":
                self.signal_params = {
                    "short": cfg.get("short", 5),
                    "long": cfg.get("long", 20),
                }
            elif self.signal_name == "rsi":
                self.signal_params = {
                    "period": cfg.get("period", 14),
                    "oversold": cfg.get("oversold", 30),
                    "overbought": cfg.get("overbought", 70),
                }
            elif self.signal_name == "momentum_breakout":
                self.signal_params = {
                    "lookback": cfg.get("lookback", 20),
                }
            elif self.signal_name == "bollinger":
                self.signal_params = {
                    "period": cfg.get("period", 20),
                    "std": cfg.get("std", 2.0),
                }
            elif self.signal_name == "macd":
                self.signal_params = {
                    "fast": cfg.get("fast", 12),
                    "slow": cfg.get("slow", 26),
                    "signal": cfg.get("signal", 9),
                }
        self.kelly_fraction = float(cfg.get("kelly_fraction", 0.25))
        self.holding_period = int(cfg.get("holding_period", 20))
        self.direction = cfg.get("direction", "long")
        self.exit_on_opposite = cfg.get("exit_on_opposite", True)
        self.allow_renewal = cfg.get("allow_renewal", True)
        self.entry_state = 1 if self.direction == "long" else -1

        # Determine max lookback for RollingWindow
        max_lookback = 100
        if self.signal_name == "golden_cross":
            max_lookback = max(
                self.signal_params.get("short", 5),
                self.signal_params.get("long", 20),
            )
        elif self.signal_name == "rsi":
            max_lookback = self.signal_params.get("period", 14) + 1
        elif self.signal_name == "momentum_breakout":
            max_lookback = self.signal_params.get("lookback", 20) + 1
        elif self.signal_name == "bollinger":
            max_lookback = self.signal_params.get("period", 20)
        elif self.signal_name == "macd":
            max_lookback = (
                self.signal_params.get("slow", 26)
                + self.signal_params.get("signal", 9)
            )
        self.price_window = RollingWindow[float](max_lookback)

        # Internal state
        self.state = 0
        self.prev_state = 0
        self.yesterday_event = 0
        self.day_counter = 0
        self.in_position = False
        self.entry_price = 0.0
        self.shares = 0.0
        self.target_exit_day_count = 0
        self.trade_log = []
        self.nav_history = []
        self.position_history = []
        self.price_history = []

        self._algo_end_date = datetime(int(end[0]), int(end[1]), int(end[2])).date()

    def OnData(self, slice):
        self.day_counter += 1

        bar = slice.Get(KrxDailyData).get(self.symbol)
        if bar is None:
            return
        price = bar.Close

        # Update price history
        self.price_window.Add(float(price))

        # Warm-up guard
        if not self.price_window.IsReady:
            self.prev_state = 0
            self.yesterday_event = 0
            return

        # Compute state
        state = get_signal(self.signal_name, list(self.price_window), **self.signal_params)
        self.state = state

        # Detect event from state change
        event = 0
        if self.prev_state != state:
            if state == self.entry_state:
                event = 1  # entry event
            elif self.prev_state == self.entry_state:
                event = -1  # exit event

        # ------------------------------------------------------------------
        # 1) Renewal: same-direction entry event yesterday extends holding period
        # ------------------------------------------------------------------
        if self.allow_renewal and self.in_position and self.yesterday_event == 1:
            self.target_exit_day_count = self.day_counter + self.holding_period

        # ------------------------------------------------------------------
        # 2) Exit checks
        # ------------------------------------------------------------------
        if self.in_position:
            should_exit = False
            exit_reason = ""

            # a) maximum holding period reached
            if self.day_counter >= self.target_exit_day_count:
                should_exit = True
                exit_reason = "holding_period"
            # b) opposite signal early exit (yesterday's exit event -> exit today)
            elif self.exit_on_opposite and self.yesterday_event == -1:
                should_exit = True
                exit_reason = "opposite_signal"
            # c) end of data
            elif self.Time.date() >= self._algo_end_date:
                should_exit = True
                exit_reason = "end_of_data"

            if should_exit:
                self._execute_exit(price, exit_reason)

        # ------------------------------------------------------------------
        # 3) New entry (yesterday's entry event -> enter today)
        # ------------------------------------------------------------------
        if not self.in_position and self.yesterday_event == 1 and self.kelly_fraction > 0:
            self._execute_entry(price)

        # ------------------------------------------------------------------
        # 4) Record daily NAV and position weight
        # ------------------------------------------------------------------
        nav = self.Portfolio.TotalPortfolioValue
        position_weight = (
            self.Portfolio[self.symbol].HoldingsValue / nav if nav > 0 else 0.0
        )
        self.nav_history.append({"date": str(self.Time.date()), "nav": float(nav)})
        self.position_history.append(
            {"date": str(self.Time.date()), "weight": float(position_weight)}
        )
        self.price_history.append({"date": str(self.Time.date()), "price": float(price)})

        # Prepare for next bar
        self.prev_state = state
        self.yesterday_event = event

    def OnEndOfAlgorithm(self):
        if self.in_position:
            self._execute_exit(self.Securities[self.symbol].Price, "end_of_data")

        # Compute summary metrics
        navs = [x["nav"] for x in self.nav_history]
        final_nav = navs[-1] if navs else float(self.Portfolio.TotalPortfolioValue)
        initial_cash = float(self.config.get("initial_cash", 1_000_000))
        total_return = (final_nav / initial_cash) - 1.0 if initial_cash > 0 else 0.0

        peak = navs[0] if navs else initial_cash
        mdd = 0.0
        for nav in navs:
            if nav > peak:
                peak = nav
            dd = (peak - nav) / peak if peak > 0 else 0.0
            if dd > mdd:
                mdd = dd

        days = len(navs)
        years = days / 252.0
        cagr = (
            (final_nav / initial_cash) ** (1.0 / years) - 1.0
            if years > 0 and initial_cash > 0
            else 0.0
        )

        results = {
            "config": self.config,
            "trade_log": self.trade_log,
            "nav_history": self.nav_history,
            "position_history": self.position_history,
            "price_history": self.price_history,
            "final_nav": final_nav,
            "total_return": total_return,
            "cagr": cagr,
            "mdd": mdd,
        }

        results_dir = "/Results"
        if not os.path.isdir(results_dir):
            results_dir = os.path.dirname(os.path.abspath(__file__))
        results_path = os.path.join(results_dir, "kelly_results.json")
        save_results(results_path, results)
        self.Log(f"Results saved to {results_path}")

    def _execute_entry(self, price):
        cash = self.Portfolio.Cash
        investment = cash * self.kelly_fraction
        if investment <= 0 or price <= 0:
            return

        quantity = investment / price
        if self.direction == "short":
            quantity = -quantity

        cost = self._apply_costs(investment)
        self.MarketOrder(self.symbol, quantity)

        self.in_position = True
        self.entry_price = price
        self.shares = abs(quantity)
        self.target_exit_day_count = self.day_counter + self.holding_period

        self.trade_log.append(
            {
                "entry_date": str(self.Time.date()),
                "entry_price": float(price),
                "shares": float(self.shares),
                "kelly_fraction": float(self.kelly_fraction),
                "entry_cost": float(cost),
                "cash_after": float(self.Portfolio.Cash),
            }
        )

    def _execute_exit(self, price, exit_reason):
        if not self.in_position:
            return

        quantity = self.Portfolio[self.symbol].Quantity
        self.MarketOrder(self.symbol, -quantity)

        trade_value = abs(quantity) * price
        cost = self._apply_costs(trade_value)

        trade_return = 0.0
        if self.entry_price > 0:
            if self.direction == "long":
                trade_return = (price - self.entry_price) / self.entry_price
            else:
                trade_return = (self.entry_price - price) / self.entry_price

        if self.trade_log and "exit_date" not in self.trade_log[-1]:
            self.trade_log[-1].update(
                {
                    "exit_date": str(self.Time.date()),
                    "exit_price": float(price),
                    "exit_reason": exit_reason,
                    "trade_return": float(trade_return),
                    "exit_cost": float(cost),
                    "cash_after": float(self.Portfolio.Cash),
                }
            )

        self.in_position = False
        self.entry_price = 0.0
        self.shares = 0.0

    def _apply_costs(self, trade_value):
        """Helper to apply commission + slippage manually."""
        COMMISSION_RATE = 0.0015
        SLIPPAGE_RATE = 0.0005
        return abs(trade_value) * (COMMISSION_RATE + SLIPPAGE_RATE)
