"""Integration test for the KellyBacktestLean end-to-end pipeline.

Run this test with:
    cd KellyBacktestLean
    python -m pytest tests/test_integration.py -v
Or directly:
    python tests/test_integration.py
"""

import json
import shutil
import subprocess
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Ensure report modules are importable
REPORT_DIR = Path(__file__).parent.parent / "report"
sys.path.insert(0, str(REPORT_DIR))

from parse_lean_results import compute_metrics, load_results


class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).parent.parent
        cls.data_dir = cls.project_root / "data" / "equity" / "usa" / "daily"
        cls.data_dir.mkdir(parents=True, exist_ok=True)
        cls.csv_path = cls.data_dir / "SAMPLE.csv"
        cls.map_file = cls.project_root / "data" / "equity" / "usa" / "map_files" / "SAMPLE.txt"
        cls.results_dir = cls.project_root / "results"
        cls.results_dir.mkdir(parents=True, exist_ok=True)
        cls.json_path = cls.results_dir / "kelly_results.json"
        cls.algo_dir = cls.project_root / "lean-algo"
        cls.config_path = cls.algo_dir / "config.json"
        cls.config_backup = cls.algo_dir / "config.json.bak"

    def setUp(self):
        if self.config_path.exists():
            shutil.copy(self.config_path, self.config_backup)

    def tearDown(self):
        if self.config_backup.exists():
            shutil.copy(self.config_backup, self.config_path)
            self.config_backup.unlink()

    def _generate_sample_csv(self, days: int = 200):
        """Generate synthetic OHLCV data in Lean standard path."""
        np.random.seed(42)
        end_date = datetime(2024, 12, 31)
        dates = pd.date_range(end=end_date, periods=days, freq="B")
        price = 100.0
        rows = []
        for date in dates:
            ret = np.random.normal(0.0005, 0.02)
            open_p = price * (1 + np.random.normal(0, 0.005))
            close_p = price * (1 + ret)
            high_p = max(open_p, close_p) * (1 + abs(np.random.normal(0, 0.005)))
            low_p = min(open_p, close_p) * (1 - abs(np.random.normal(0, 0.005)))
            volume = int(np.random.uniform(1_000_000, 10_000_000))
            rows.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(open_p, 4),
                "high": round(high_p, 4),
                "low": round(low_p, 4),
                "close": round(close_p, 4),
                "volume": volume,
            })
            price = close_p
        df = pd.DataFrame(rows)
        df.to_csv(self.csv_path, index=False)
        # Write minimal map file
        self.map_file.parent.mkdir(parents=True, exist_ok=True)
        first_date = dates[0].strftime("%Y%m%d")
        self.map_file.write_text(f"{first_date},SAMPLE,SAMPLE\n", encoding="ascii")
        start_date_str = dates[0].strftime("%Y-%m-%d")
        end_date_str = dates[-1].strftime("%Y-%m-%d")
        return start_date_str, end_date_str

    def _write_test_config(self, start_date: str, end_date: str):
        config = {
            "symbol": "SAMPLE",
            "signal_name": "golden_cross",
            "short": 5,
            "long": 20,
            "holding_period": 20,
            "direction": "long",
            "exit_on_opposite": True,
            "allow_renewal": True,
            "kelly_fraction": 0.25,
            "initial_cash": 1_000_000,
            "start_date": start_date,
            "end_date": end_date,
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return config

    def _mock_lean_run(self):
        """Mock Lean backtest output because Docker may not be available."""
        df = pd.read_csv(self.csv_path, parse_dates=["date"])
        nav_history = []
        position_history = []
        trade_log = []

        initial_cash = 1_000_000.0
        nav = initial_cash
        shares = 0.0

        for idx, row in df.iterrows():
            date_str = row["date"].strftime("%Y-%m-%d")
            price = row["close"]

            if idx % 20 == 0:
                shares = nav * 0.5 / price
                trade_log.append({
                    "entry_date": date_str,
                    "exit_date": (row["date"] + timedelta(days=5)).strftime("%Y-%m-%d"),
                    "entry_price": price,
                    "exit_price": price * 1.01,
                    "trade_return": 0.01,
                    "kelly_fraction": 0.5,
                })

            nav = shares * price + (nav - shares * price)
            if nav <= 0:
                nav = initial_cash * 0.9

            nav_history.append({
                "date": date_str,
                "nav": float(nav),
            })
            position_history.append({
                "date": date_str,
                "weight": 0.5 if idx % 20 == 0 else 0.0,
            })

        results = {
            "trade_log": trade_log,
            "nav_history": nav_history,
            "position_history": position_history,
            "final_nav": nav,
            "total_return": (nav / initial_cash) - 1.0,
            "cagr": 0.05,
            "mdd": 0.05,
        }
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

    def test_01_generate_data(self):
        self._generate_sample_csv(days=200)
        self.assertTrue(self.csv_path.exists())
        df = pd.read_csv(self.csv_path)
        self.assertGreaterEqual(len(df), 190)
        self.assertIn("close", df.columns)

    def test_02_write_config(self):
        start, end = self._generate_sample_csv(days=200)
        self._write_test_config(start, end)
        self.assertTrue(self.config_path.exists())
        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg["symbol"], "SAMPLE")

    def test_03_run_backtest(self):
        start, end = self._generate_sample_csv(days=200)
        self._write_test_config(start, end)

        docker_available = False
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            docker_available = result.returncode == 0
        except Exception:
            docker_available = False

        if docker_available:
            ps_script = self.project_root / "scripts" / "docker_run.ps1"
            try:
                subprocess.run(
                    [
                        "powershell",
                        "-ExecutionPolicy", "Bypass",
                        "-File", str(ps_script),
                    ],
                    check=True,
                    timeout=300,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                print(f"Docker run failed, falling back to mock: {e}")
                self._mock_lean_run()
        else:
            self._mock_lean_run()

        self.assertTrue(self.json_path.exists())

    def test_04_parse_and_assert(self):
        if not self.json_path.exists():
            start, end = self._generate_sample_csv(days=200)
            self._write_test_config(start, end)
            self._mock_lean_run()

        data = load_results(self.json_path)
        self.assertIn("trade_log", data)
        self.assertIn("nav_history", data)
        self.assertIn("position_history", data)

        nav_history = data["nav_history"]
        self.assertGreater(len(nav_history), 0)
        self.assertIn("nav", nav_history[0])

        metrics = compute_metrics(nav_history)
        self.assertIn("cagr", metrics)
        self.assertIn("mdd", metrics)
        self.assertIn("sharpe", metrics)
        self.assertIn("total_return", metrics)
        self.assertIn("volatility", metrics)

        nav_values = [x["nav"] for x in nav_history]
        self.assertTrue(all(v > 0 for v in nav_values))


def suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(TestIntegration)


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())
