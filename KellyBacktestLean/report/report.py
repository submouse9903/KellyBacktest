"""Generate a static HTML report from Lean backtest results."""

import argparse
import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import gaussian_kde

from parse_lean_results import compute_kelly_metrics, compute_metrics, kelly_curve_data, load_results, summarize_trades


def _nav_series(nav_history: list[dict]) -> pd.Series:
    df = pd.DataFrame(nav_history)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df["nav"]


def _buyhold_series(nav_history: list[dict]) -> pd.Series | None:
    df = pd.DataFrame(nav_history)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df["buyhold"] if "buyhold" in df.columns else None


def _position_series(position_history: list[dict]) -> pd.Series:
    df = pd.DataFrame(position_history)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df["weight"]


def fig_nav_vs_buyhold(nav_history: list[dict]) -> go.Figure:
    nav = _nav_series(nav_history)
    buyhold = _buyhold_series(nav_history)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=nav.index, y=nav.values, mode="lines",
            name="Kelly Strategy", line=dict(color="#1f77b4", width=2),
        ),
        secondary_y=False,
    )

    if buyhold is not None:
        fig.add_trace(
            go.Scatter(
                x=buyhold.index, y=buyhold.values, mode="lines",
                name="Buy & Hold", line=dict(color="#ff7f0e", width=2, dash="dot"),
            ),
            secondary_y=False,
        )

    cummax = nav.cummax()
    drawdown = (nav - cummax) / cummax * 100
    fig.add_trace(
        go.Scatter(
            x=drawdown.index, y=drawdown.values, mode="lines",
            fill="tozeroy", name="Drawdown",
            line=dict(color="#d62728", width=1),
            fillcolor="rgba(214, 39, 40, 0.15)",
            hovertemplate="%{y:.1f}%<extra>Drawdown</extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="NAV vs Buy & Hold",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
    )
    fig.update_yaxes(title_text="Portfolio Value", secondary_y=False)
    fig.update_yaxes(title_text="Drawdown (%)", secondary_y=True)
    return fig


def fig_drawdown(nav_history: list[dict]) -> go.Figure:
    nav = _nav_series(nav_history)
    cummax = nav.cummax()
    drawdown = (nav - cummax) / cummax * 100

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=drawdown.index, y=drawdown.values, mode="lines",
            fill="tozeroy", name="Drawdown",
            line=dict(color="#d62728", width=1),
            fillcolor="rgba(214, 39, 40, 0.2)",
        )
    )
    fig.update_layout(
        title="Drawdown Over Time",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        hovermode="x unified",
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def fig_position_weight(position_history: list[dict]) -> go.Figure:
    pos = _position_series(position_history)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=pos.index, y=pos.values * 100, mode="lines",
            fill="tozeroy", name="Position Weight",
            line=dict(color="#2ca02c", width=1.5),
            fillcolor="rgba(44, 160, 44, 0.2)",
        )
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title="Position Weight Over Time",
        xaxis_title="Date",
        yaxis_title="Weight (%)",
        hovermode="x unified",
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def fig_trade_returns_histogram(trade_log: list[dict]) -> go.Figure:
    returns = pd.Series([t.get("trade_return", 0.0) for t in trade_log]).dropna()
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=returns.values,
            nbinsx=max(10, min(50, len(returns) // 2)),
            histnorm="density",
            name="Histogram",
            marker_color="#1f77b4",
            opacity=0.6,
        )
    )
    if len(returns) >= 3:
        kde = gaussian_kde(returns.values)
        x_range = np.linspace(returns.min(), returns.max(), 200)
        fig.add_trace(
            go.Scatter(
                x=x_range,
                y=kde(x_range),
                mode="lines",
                name="KDE",
                line=dict(color="#ff7f0e", width=2),
            )
        )
    fig.add_vline(
        x=returns.mean(), line_dash="dash", line_color="#2ca02c",
        annotation_text="Mean", annotation_position="top"
    )
    fig.add_vline(
        x=returns.median(), line_dash="dot", line_color="#d62728",
        annotation_text="Median", annotation_position="top right"
    )
    fig.update_layout(
        title="Trade Returns Distribution",
        xaxis_title="Trade Return (소수)",
        yaxis_title="Density",
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def fig_kelly_curve(f_vals: np.ndarray, exp_log: np.ndarray, f_star: float | None = None) -> go.Figure:
    fig = go.Figure()
    valid_mask = np.isfinite(exp_log)
    fig.add_trace(
        go.Scatter(
            x=f_vals[valid_mask],
            y=exp_log[valid_mask],
            mode="lines",
            name="E[log(1+fX)]",
            line=dict(color="#1f77b4", width=2),
            fill="tozeroy",
            fillcolor="rgba(31, 119, 180, 0.1)",
        )
    )
    if f_star is not None and np.isfinite(f_star):
        idx = np.argmin(np.abs(f_vals - f_star))
        if np.isfinite(exp_log[idx]):
            fig.add_vline(
                x=f_star, line_dash="dash", line_color="#d62728",
                annotation_text=f"f*={f_star:.2f}",
            )
            fig.add_trace(
                go.Scatter(
                    x=[f_star],
                    y=[exp_log[idx]],
                    mode="markers",
                    marker=dict(color="#d62728", size=12),
                    name="Optimal f*",
                    showlegend=False,
                )
            )
    fig.update_layout(
        title="Kelly Criterion Curve",
        xaxis_title="f (Kelly Ratio)",
        yaxis_title="E[log(1 + fX)]",
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def _fig_to_html_div(fig: go.Figure) -> str:
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def generate_html_report(data: dict[str, Any]) -> str:
    """Build a self-contained HTML string from parsed Lean results."""
    nav_history = data.get("nav_history", [])
    position_history = data.get("position_history", [])
    trade_log = data.get("trade_log", [])

    metrics = compute_metrics(nav_history)
    trade_summary = summarize_trades(trade_log)
    kelly_metrics = compute_kelly_metrics(trade_log)

    nav_fig = fig_nav_vs_buyhold(nav_history)
    dd_fig = fig_drawdown(nav_history)
    pos_fig = fig_position_weight(position_history)
    hist_fig = fig_trade_returns_histogram(trade_log)

    nav_div = _fig_to_html_div(nav_fig)
    dd_div = _fig_to_html_div(dd_fig)
    pos_div = _fig_to_html_div(pos_fig)
    hist_div = _fig_to_html_div(hist_fig)

    f_vals, exp_log = kelly_curve_data(trade_log)
    if kelly_metrics["valid"] and len(f_vals) > 0:
        kelly_curve_fig = fig_kelly_curve(f_vals, exp_log, f_star=kelly_metrics["f_star_numerical"])
        kelly_curve_div = _fig_to_html_div(kelly_curve_fig)
    else:
        kelly_curve_div = "<p>거래 수익률 부족으로 켈리 곡선을 생성할 수 없습니다.</p>"

    metrics_rows = "\n".join(
        f"<tr><td>{k}</td><td>{v:.4f}</td></tr>"
        for k, v in metrics.items()
    )
    trade_rows = "\n".join(
        f"<tr><td>{k}</td><td>{v:.4f}</td></tr>"
        for k, v in trade_summary.items()
    )
    kelly_rows = "\n".join(
        f"<tr><td>{k}</td><td>{v:.4f}</td></tr>"
        for k, v in kelly_metrics.items() if k != "valid"
    )

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>KellyBacktestLean Report</title>
    <style>
        body {{ font-family: "Segoe UI", sans-serif; margin: 2rem; background: #f8f9fa; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; margin-top: 2rem; }}
        .section {{ background: #fff; padding: 1.5rem; border-radius: 8px; margin-bottom: 1.5rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        table {{ border-collapse: collapse; width: 100%; max-width: 400px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>📈 KellyBacktestLean Report</h1>
    <p>Generated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

    <div class="section">
        <h2>Performance Metrics</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            {metrics_rows}
        </table>
    </div>

    <div class="section">
        <h2>Trade Summary</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            {trade_rows}
        </table>
    </div>

    <div class="section">
        <h2>NAV vs Buy & Hold</h2>
        {nav_div}
    </div>

    <div class="section">
        <h2>Drawdown</h2>
        {dd_div}
    </div>

    <div class="section">
        <h2>Position Weight</h2>
        {pos_div}
    </div>

    <div class="section">
        <h2>Trade Returns Histogram</h2>
        {hist_div}
    </div>

    <div class="section">
        <h2>Kelly Metrics</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            {kelly_rows}
        </table>
    </div>

    <div class="section">
        <h2>Kelly Curve</h2>
        {kelly_curve_div}
    </div>
</body>
</html>"""
    return html


def main():
    parser = argparse.ArgumentParser(description="Generate HTML report from Lean backtest results.")
    parser.add_argument("--input", required=True, help="Path to kelly_results.json")
    parser.add_argument("--output", default="report.html", help="Output HTML file path")
    args = parser.parse_args()

    data = load_results(args.input)
    html = generate_html_report(data)

    out_path = Path(args.output)
    out_path.write_text(html, encoding="utf-8")
    print(f"Report written to {out_path.resolve()}")


if __name__ == "__main__":
    main()
