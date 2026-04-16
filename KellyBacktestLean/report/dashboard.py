"""Streamlit dashboard for KellyBacktestLean results."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from parse_lean_results import (
    compute_kelly_metrics,
    compute_metrics,
    kelly_curve_data,
    load_results,
    summarize_trades,
)
from report import (
    fig_drawdown,
    fig_kelly_curve,
    fig_nav_vs_buyhold,
    fig_position_weight,
    fig_trade_returns_histogram,
)

st.set_page_config(page_title="KellyBacktestLean Dashboard", layout="wide")
st.title("📈 KellyBacktestLean Dashboard")
st.markdown("**QuantConnect Lean 백테스트 결과 및 Grid Search 결과를 실시간으로 시각화합니다.**")

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
RESULTS_DIR = PROJECT_ROOT / "results"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def scan_result_files() -> list[str]:
    if not RESULTS_DIR.exists():
        return []
    files = sorted([p.name for p in RESULTS_DIR.glob("kelly_results*.json")])
    return files


def auto_load_latest_result():
    """Automatically load the most recent kelly_results*.json."""
    files = scan_result_files()
    if not files:
        return None
    # Prefer exact 'kelly_results.json', otherwise the last sorted file
    target = "kelly_results.json" if "kelly_results.json" in files else files[-1]
    try:
        return load_results(str(RESULTS_DIR / target))
    except Exception:
        return None


def format_percent(x):
    return f"{x*100:.2f}%"


# ---------------------------------------------------------------------------
# Auto-load data on start
# ---------------------------------------------------------------------------
data = auto_load_latest_result()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 설정")

    # --- Saved Strategies ---
    st.subheader("💾 저장된 전략")
    result_files = scan_result_files()
    strategy_labels = {}
    for f in result_files:
        # Try to build a friendly label from the JSON content
        try:
            tmp = load_results(str(RESULTS_DIR / f))
            cfg = tmp.get("config", {}) if isinstance(tmp, dict) else {}
            sym = cfg.get("symbol", "?")
            sig = cfg.get("signal_name", "?")
            label = f"{sig} ({sym})"
        except Exception:
            label = f
        strategy_labels[label] = f

    if strategy_labels:
        default_label = next(
            (k for k, v in strategy_labels.items() if v == "kelly_results.json"),
            list(strategy_labels.keys())[0],
        )
        selected_label = st.radio("전략 선택", list(strategy_labels.keys()), index=list(strategy_labels.keys()).index(default_label))
        selected_json = strategy_labels[selected_label]
        try:
            data = load_results(str(RESULTS_DIR / selected_json))
        except Exception as e:
            st.error(f"JSON 로딩 오류: {e}")
            data = None
    else:
        st.warning("저장된 전략이 없습니다.")
        data = None
        selected_label = None

    st.divider()
    uploaded_csv = st.file_uploader("Grid Search CSV 업로드", type=["csv"])

    st.divider()
    st.caption(f"Project root: `{PROJECT_ROOT}`")


# ---------------------------------------------------------------------------
# Grid Search CSV load (if uploaded)
# ---------------------------------------------------------------------------
grid_df = None
if uploaded_csv is not None:
    try:
        grid_df = pd.read_csv(uploaded_csv)
    except Exception as e:
        st.error(f"CSV 로딩 오류: {e}")


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------
if data is None:
    st.info(
        "아직 Lean 백테스트 결과가 없습니다. "
        "`scripts/docker_run.ps1` 또는 `orchestrator/run_single_backtest.py`를 실행해주세요."
    )
    st.stop()

if not isinstance(data, dict):
    st.error(f"선택한 JSON 파일의 최상위 구조가 dict가 아닙니다. (실제 타입: {type(data).__name__}). Kelly 결과 JSON 파일을 선택했는지 확인하세요.")
    st.stop()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_strategy, tab_backtest, tab_metrics, tab_grid = st.tabs(
    ["📈 전략 분석", "📉 백테스트 결과", "📋 성과 지표", "🔍 Grid Search 결과"]
)

# --- Strategy Analysis tab ---
with tab_strategy:
    st.subheader("전략 개요")
    config = data.get("config", {})
    trade_log = data.get("trade_log", [])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**알고리즘 파라미터**")
        if config:
            cfg_df = pd.DataFrame({"Parameter": list(config.keys()), "Value": list(config.values())})
            cfg_df["Value"] = cfg_df["Value"].astype(str)
            st.dataframe(cfg_df, use_container_width=True, hide_index=True)
        else:
            st.info("config 정보가 없습니다.")

    with col2:
        st.markdown("**거래 요약 (Trade Summary)**")
        summary = summarize_trades(trade_log)
        if summary["n_trades"] > 0:
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("총 거래 수", f"{summary['n_trades']}회")
            s2.metric("승률", f"{summary['win_rate']*100:.1f}%")
            s3.metric("평균 수익", format_percent(summary["avg_win"]))
            s4.metric("평균 손실", format_percent(summary["avg_loss"]))

            st.markdown("**Profit Factor**")
            pf = summary["profit_factor"]
            if pf == float("inf"):
                st.success("∞ (무한대)")
            else:
                st.write(f"{pf:.2f}")
        else:
            st.info("거래 기록이 없습니다.")

    st.divider()
    st.markdown("**원본 Config (JSON)**")
    st.json(config)


# --- Backtest Results tab ---
with tab_backtest:
    nav_history = data.get("nav_history", [])
    position_history = data.get("position_history", [])
    trade_log = data.get("trade_log", [])

    if nav_history:
        nav = pd.DataFrame(nav_history)
        nav["date"] = pd.to_datetime(nav["date"])
        nav = nav.set_index("date").sort_index()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("최종 자본", f"{nav['nav'].iloc[-1]:,.0f}")
        with col2:
            total_ret = nav["nav"].iloc[-1] / nav["nav"].iloc[0] - 1
            st.metric("총 수익률", format_percent(total_ret))
        with col3:
            cummax = nav["nav"].cummax()
            mdd = ((nav["nav"] - cummax) / cummax).min()
            st.metric("MDD", format_percent(mdd))
        with col4:
            st.metric("거래 횟수", f"{len(trade_log)}회")

        st.divider()

        nav_log_scale = st.toggle("로그 스케일", value=False, key="nav_log")
        show_dd = st.toggle("Drawdown 오버레이", value=True, key="nav_dd")

        # NAV chart with optional toggles
        fig_nav = make_subplots(specs=[[{"secondary_y": True}]])
        fig_nav.add_trace(
            go.Scatter(
                x=nav.index,
                y=nav["nav"],
                mode="lines",
                name="Kelly Strategy",
                line=dict(color="#1f77b4", width=2),
            ),
            secondary_y=False,
        )
        if "buyhold" in nav.columns:
            fig_nav.add_trace(
                go.Scatter(
                    x=nav.index,
                    y=nav["buyhold"],
                    mode="lines",
                    name="Buy & Hold",
                    line=dict(color="#ff7f0e", width=2, dash="dot"),
                ),
                secondary_y=False,
            )
        if show_dd:
            cummax = nav["nav"].cummax()
            drawdown = (nav["nav"] - cummax) / cummax * 100
            fig_nav.add_trace(
                go.Scatter(
                    x=drawdown.index,
                    y=drawdown.values,
                    mode="lines",
                    fill="tozeroy",
                    name="Drawdown",
                    line=dict(color="#d62728", width=1),
                    fillcolor="rgba(214, 39, 40, 0.15)",
                ),
                secondary_y=True,
            )
        fig_nav.update_yaxes(
            title_text="Portfolio Value",
            type="log" if nav_log_scale else "linear",
            secondary_y=False,
        )
        fig_nav.update_yaxes(title_text="Drawdown (%)", secondary_y=True)
        fig_nav.update_layout(
            title="NAV vs Buy & Hold",
            hovermode="x unified",
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=80, b=40),
        )
        st.plotly_chart(fig_nav, use_container_width=True)

        if position_history:
            st.plotly_chart(fig_position_weight(position_history), use_container_width=True)

        price_history = data.get("price_history", [])
        if price_history and trade_log:
            st.subheader("가격 차트 + 거래 마커")
            price_df = pd.DataFrame(price_history)
            price_df["date"] = pd.to_datetime(price_df["date"])
            price_df = price_df.set_index("date").sort_index()

            tdf = pd.DataFrame(trade_log)
            entry_dates = pd.to_datetime(tdf["entry_date"]) if "entry_date" in tdf.columns else []
            entry_prices = tdf["entry_price"] if "entry_price" in tdf.columns else []
            exit_dates = pd.to_datetime(tdf["exit_date"]) if "exit_date" in tdf.columns else []
            exit_prices = tdf["exit_price"] if "exit_price" in tdf.columns else []

            fig_price = go.Figure()
            fig_price.add_trace(
                go.Scatter(
                    x=price_df.index,
                    y=price_df["price"],
                    mode="lines",
                    name="Price",
                    line=dict(color="#3366cc", width=1.5),
                )
            )
            if len(entry_dates) > 0:
                fig_price.add_trace(
                    go.Scatter(
                        x=entry_dates,
                        y=entry_prices,
                        mode="markers",
                        name="진입 (Entry)",
                        marker=dict(color="#2ca02c", symbol="triangle-up", size=12, line=dict(width=1, color="darkgreen")),
                    )
                )
            if len(exit_dates) > 0:
                fig_price.add_trace(
                    go.Scatter(
                        x=exit_dates,
                        y=exit_prices,
                        mode="markers",
                        name="청산 (Exit)",
                        marker=dict(color="#d62728", symbol="triangle-down", size=12, line=dict(width=1, color="darkred")),
                    )
                )
            fig_price.update_layout(
                title="Price with Trade Markers",
                xaxis_title="Date",
                yaxis_title="Price",
                hovermode="x unified",
                template="plotly_white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=40, r=40, t=80, b=40),
            )
            st.plotly_chart(fig_price, use_container_width=True)

        st.subheader("거래 내역")
        if trade_log:
            tdf = pd.DataFrame(trade_log)
            for col in ["trade_return", "kelly_fraction"]:
                if col in tdf.columns:
                    tdf[col] = tdf[col].apply(format_percent)
            for col in ["entry_price", "exit_price"]:
                if col in tdf.columns:
                    tdf[col] = tdf[col].apply(lambda x: f"{x:,.2f}")
            for col in ["entry_cost", "exit_cost", "cash_after"]:
                if col in tdf.columns:
                    tdf[col] = tdf[col].apply(lambda x: f"{x:,.2f}")
            st.dataframe(tdf, use_container_width=True)
        else:
            st.warning("거래 기록이 없습니다.")
    else:
        st.warning("nav_history가 비어 있습니다.")


# --- Performance Metrics tab ---
with tab_metrics:
    nav_history = data.get("nav_history", [])
    trade_log = data.get("trade_log", [])

    if nav_history:
        metrics = compute_metrics(nav_history)
        trade_summary = summarize_trades(trade_log)
        kelly_metrics = compute_kelly_metrics(trade_log)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("성과 지표")
            mdf = pd.DataFrame(
                {
                    "지표": ["CAGR", "MDD", "Sharpe", "총 수익률", "변동성(연)"],
                    "값": [
                        format_percent(metrics["cagr"]),
                        format_percent(metrics["mdd"]),
                        f"{metrics['sharpe']:.2f}",
                        format_percent(metrics["total_return"]),
                        format_percent(metrics["volatility"]),
                    ],
                }
            )
            st.dataframe(mdf, use_container_width=True, hide_index=True)

        with col2:
            st.subheader("거래 통계")
            tdf = pd.DataFrame(
                {
                    "지표": ["총 거래 수", "승률", "평균 수익", "평균 손실", "Profit Factor"],
                    "값": [
                        f"{trade_summary['n_trades']}회",
                        f"{trade_summary['win_rate']*100:.1f}%",
                        format_percent(trade_summary["avg_win"]),
                        format_percent(trade_summary["avg_loss"]),
                        "∞" if trade_summary["profit_factor"] == float("inf") else f"{trade_summary['profit_factor']:.2f}",
                    ],
                }
            )
            st.dataframe(tdf, use_container_width=True, hide_index=True)

        st.subheader("📊 켈리 기준 분석")
        if kelly_metrics["valid"]:
            kcol1, kcol2, kcol3 = st.columns([1, 1, 2])
            with kcol1:
                st.metric("Numerical Kelly (f*)", f"{kelly_metrics['f_star_numerical']*100:.1f}%")
            with kcol2:
                st.metric("정규분포 근삿값", f"{kelly_metrics['f_star_normal_approx']*100:.1f}%")
            with kcol3:
                st.caption("회색 값은 '정규분포 가정 시 근사값'이며, 기본 값은 Numerical 최적화 결과입니다.")

            stat_col1, stat_col2, stat_col3, stat_col4, stat_col5 = st.columns(5)
            with stat_col1:
                st.metric("평균", f"{kelly_metrics['mean']*100:.2f}%")
            with stat_col2:
                st.metric("중앙값", f"{kelly_metrics['median']*100:.2f}%")
            with stat_col3:
                st.metric("표준편차", f"{kelly_metrics['std']*100:.2f}%")
            with stat_col4:
                st.metric("왜도", f"{kelly_metrics['skewness']:.2f}")
            with stat_col5:
                st.metric("첨도", f"{kelly_metrics['kurtosis']:.2f}")

            st.info(
                "💡 **Numerical Kelly**는 전체 거래 수익률 분포에서 $E[\\log(1+fX)]$를 직접 최적화한 값입니다. "
                "승률·평균손익비 공식과 다를 수 있으며, 분포의 꼬리와 스큐에 민감하게 반응합니다."
            )
        else:
            st.warning("거래 수익률이 부족하여 켈리 기준 분석을 수행할 수 없습니다.")

        st.plotly_chart(fig_drawdown(nav_history), use_container_width=True)
        if trade_log:
            st.plotly_chart(fig_trade_returns_histogram(trade_log), use_container_width=True)
            f_vals, exp_log = kelly_curve_data(trade_log)
            if len(f_vals) > 0 and kelly_metrics["valid"]:
                st.plotly_chart(
                    fig_kelly_curve(f_vals, exp_log, f_star=kelly_metrics["f_star_numerical"]),
                    use_container_width=True,
                )
    else:
        st.warning("nav_history가 비어 있습니다.")


# --- Grid Search Results tab ---
with tab_grid:
    st.subheader("Grid Search Results")
    if grid_df is not None and not grid_df.empty:
        st.success(f"{len(grid_df)}개의 조합을 로드했습니다.")

        # Column filters
        numeric_cols = grid_df.select_dtypes(include=["number"]).columns.tolist()
        if numeric_cols:
            c1, c2 = st.columns([1, 3])
            with c1:
                filter_col = st.selectbox("필터 컬럼", numeric_cols, key="grid_filter_col")
            with c2:
                min_val = float(grid_df[filter_col].min())
                max_val = float(grid_df[filter_col].max())
                threshold = st.slider(
                    f"{filter_col} 최소값",
                    min_val,
                    max_val,
                    min_val,
                    key="grid_filter_threshold",
                )
            filtered = grid_df[grid_df[filter_col] >= threshold]
            st.write(f"필터 후 **{len(filtered)}개** 조합")
            st.dataframe(filtered, use_container_width=True)

            # Simple bar chart of top N by f_star_adjusted
            if "f_star_adjusted" in filtered.columns:
                top_n = filtered.sort_values("f_star_adjusted", ascending=False).head(20)
                fig_bar = go.Figure()
                fig_bar.add_trace(
                    go.Bar(
                        x=top_n.index.astype(str),
                        y=top_n["f_star_adjusted"] * 100,
                        marker_color="#1f77b4",
                        name="f* (%)",
                    )
                )
                fig_bar.update_layout(
                    title="Top 20 f* (Adjusted Kelly)",
                    xaxis_title="조합 인덱스",
                    yaxis_title="f* (%)",
                    template="plotly_white",
                    margin=dict(l=40, r=40, t=60, b=40),
                )
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.dataframe(grid_df, use_container_width=True)
    else:
        st.info("Grid Search CSV를 업로드하면 결과가 표시됩니다.")
