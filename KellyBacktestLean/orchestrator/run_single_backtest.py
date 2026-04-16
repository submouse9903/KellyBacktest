"""Run a single Lean backtest via Docker.

Writes the provided config dict to KellyBacktestLean/lean-algo/config.json,
invokes the quantconnect/lean:latest Docker image, waits for completion,
and reads the resulting JSON from KellyBacktestLean/results/kelly_results.json.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Resolve project paths
ORCHESTRATOR_DIR = Path(__file__).parent.resolve()
LEAN_DIR = ORCHESTRATOR_DIR.parent
ALGO_DIR = LEAN_DIR / "lean-algo"
RESULTS_DIR = LEAN_DIR / "results"
DATA_DIR = LEAN_DIR / "data"
CONFIG_PATH = ALGO_DIR / "config.json"
RESULTS_PATH = RESULTS_DIR / "kelly_results.json"

# Default Docker image
LEAN_IMAGE = "quantconnect/lean:latest"


def run_single_backtest(
    config: dict,
    docker_image: str = LEAN_IMAGE,
    timeout: Optional[int] = 300,
    verbose: bool = True,
) -> dict:
    """Run one Lean backtest with the given configuration.

    Args:
        config: Dictionary written to lean-algo/config.json.
        docker_image: Docker image to use.
        timeout: Timeout in seconds for the docker run.
        verbose: Whether to print progress messages.

    Returns:
        Parsed results dict from results/kelly_results.json.

    Raises:
        FileNotFoundError: If the results file does not appear after the run.
        subprocess.TimeoutExpired: If the docker run exceeds the timeout.
        RuntimeError: If the docker run returns a non-zero exit code.
    """
    # Ensure directories exist
    ALGO_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Remove stale results file so we don't accidentally read an old one
    if RESULTS_PATH.exists():
        RESULTS_PATH.unlink()

    # Write config
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    if verbose:
        print(f"[run_single_backtest] Wrote config to {CONFIG_PATH}")

    # Build PowerShell-compatible docker command
    # Using string form with subprocess.run on Windows so path resolution is straightforward.
    lean_dir_str = str(LEAN_DIR)
    data_mount = f"{lean_dir_str}/data:/Data"
    algo_mount = f"{lean_dir_str}/lean-algo:/Lean/Launcher/bin/Debug/Algorithms"
    results_mount = f"{lean_dir_str}/results:/Results"

    cmd = (
        f'docker run --rm '
        f'-v "{data_mount}" '
        f'-v "{algo_mount}" '
        f'-v "{results_mount}" '
        f'-e PYTHONPATH=/Lean/Launcher/bin/Debug/Algorithms '
        f'{docker_image} '
        f'--config=/Lean/Launcher/bin/Debug/Algorithms/lean_launcher_config.json'
    )

    if verbose:
        print(f"[run_single_backtest] Running: {cmd}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=not verbose,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise subprocess.TimeoutExpired(
            cmd=cmd, timeout=timeout, output=exc.output, stderr=exc.stderr
        ) from exc

    if result.returncode != 0:
        stderr = result.stderr or ""
        raise RuntimeError(f"Lean docker run failed (exit {result.returncode}): {stderr}")

    if not RESULTS_PATH.exists():
        raise FileNotFoundError(
            f"Results file not found after backtest: {RESULTS_PATH}"
        )

    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        backtest_results = json.load(f)

    if verbose:
        print(f"[run_single_backtest] Loaded results from {RESULTS_PATH}")

    return backtest_results


if __name__ == "__main__":
    # Minimal sanity check using a dummy config (does not require real data)
    dummy_config = {
        "symbol": "005930",
        "start_date": "2020-01-02",
        "end_date": "2023-12-31",
        "signal_name": "golden_cross",
        "short": 5,
        "long": 20,
        "holding_period": 20,
        "direction": "long",
        "exit_on_opposite": True,
        "allow_renewal": True,
        "kelly_fraction": 0.25,
        "initial_cash": 1_000_000,
    }
    try:
        results = run_single_backtest(dummy_config, verbose=True)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)
