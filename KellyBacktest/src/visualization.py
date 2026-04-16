"""Plotly 기반 시각화 유틸리티"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import gaussian_kde


def plot_nav_comparison(
    nav_kelly: pd.Series,
    nav_buyhold: pd.Series,
    log_scale: bool = False,
    show_drawdown: bool = True,
) -> go.Figure:
    """누적 자산 곡선 비교 (선택적으로 Drawdown 오버레이 및 로그 스케일)"""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Kelly Strategy
    fig.add_trace(
        go.Scatter(
            x=nav_kelly.index,
            y=nav_kelly.values,
            mode="lines",
            name="Kelly Strategy",
            line=dict(color="#1f77b4", width=2),
        ),
        secondary_y=False,
    )

    # Buy & Hold
    fig.add_trace(
        go.Scatter(
            x=nav_buyhold.index,
            y=nav_buyhold.values,
            mode="lines",
            name="Buy & Hold",
            line=dict(color="#ff7f0e", width=2, dash="dot"),
        ),
        secondary_y=False,
    )

    # Drawdown overlay
    if show_drawdown:
        cummax = nav_kelly.cummax()
        drawdown = (nav_kelly - cummax) / cummax * 100
        fig.add_trace(
            go.Scatter(
                x=drawdown.index,
                y=drawdown.values,
                mode="lines",
                fill="tozeroy",
                name="Kelly Drawdown",
                line=dict(color="#d62728", width=1),
                fillcolor="rgba(214, 39, 40, 0.15)",
                hovertemplate="%{y:.1f}%<extra>Drawdown</extra>",
            ),
            secondary_y=True,
        )

    fig.update_layout(
        title="자기자본(NAV) 변화 및 낙폭",
        xaxis_title="날짜",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    fig.update_yaxes(
        title_text="포트폴리오 가치", secondary_y=False, type="log" if log_scale else "linear"
    )
    fig.update_yaxes(title_text="낙폭 (%)", secondary_y=True)

    return fig


def plot_equity_growth(nav_kelly: pd.Series, nav_buyhold: pd.Series) -> go.Figure:
    """초기 자본 대비 성장률(%) 비교"""
    growth_kelly = (nav_kelly / nav_kelly.iloc[0] - 1) * 100
    growth_bh = (nav_buyhold / nav_buyhold.iloc[0] - 1) * 100

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=growth_kelly.index,
            y=growth_kelly.values,
            mode="lines",
            name="Kelly Strategy",
            line=dict(color="#1f77b4", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=growth_bh.index,
            y=growth_bh.values,
            mode="lines",
            name="Buy & Hold",
            line=dict(color="#ff7f0e", width=2, dash="dot"),
        )
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title="초기 자본 대비 수익률 (%)",
        xaxis_title="날짜",
        yaxis_title="수익률 (%)",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def plot_price_with_signals(
    prices: pd.Series, signals: pd.Series, title: str = "가격 및 신호"
) -> go.Figure:
    """가격 차트에 매수/매도 신호 마커 표시"""
    fig = go.Figure()

    # 가격선
    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=prices.values,
            mode="lines",
            name="종가",
            line=dict(color="#333333", width=1.5),
        )
    )

    # 매수 신호 (+1)
    buy_signals = prices[signals == 1]
    if not buy_signals.empty:
        fig.add_trace(
            go.Scatter(
                x=buy_signals.index,
                y=buy_signals.values,
                mode="markers",
                name="매수 신호",
                marker=dict(color="green", size=10, symbol="triangle-up"),
            )
        )

    # 매도 신호 (-1)
    sell_signals = prices[signals == -1]
    if not sell_signals.empty:
        fig.add_trace(
            go.Scatter(
                x=sell_signals.index,
                y=sell_signals.values,
                mode="markers",
                name="매도 신호",
                marker=dict(color="red", size=10, symbol="triangle-down"),
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="날짜",
        yaxis_title="가격",
        hovermode="x unified",
        template="plotly_white",
    )
    return fig


def plot_position_history(position: pd.Series) -> go.Figure:
    """일별 포지션 비중 변화"""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=position.index,
            y=position.values * 100,
            mode="lines",
            fill="tozeroy",
            name="포지션 비중",
            line=dict(color="#2ca02c", width=1.5),
            fillcolor="rgba(44, 160, 44, 0.2)",
        )
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title="일별 포지션 비중",
        xaxis_title="날짜",
        yaxis_title="비중 (%)",
        hovermode="x unified",
        template="plotly_white",
    )
    return fig


def plot_drawdown(nav: pd.Series) -> go.Figure:
    """낙폭(Drawdown) 그래프"""
    cummax = nav.cummax()
    drawdown = (nav - cummax) / cummax * 100

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=drawdown.index,
            y=drawdown.values,
            mode="lines",
            fill="tozeroy",
            name="Drawdown",
            line=dict(color="#d62728", width=1),
            fillcolor="rgba(214, 39, 40, 0.2)",
        )
    )
    fig.update_layout(
        title="최대 낙폭 (Drawdown)",
        xaxis_title="날짜",
        yaxis_title="낙폭 (%)",
        hovermode="x unified",
        template="plotly_white",
    )
    return fig


def plot_portfolio_weights(weights_df: pd.DataFrame) -> go.Figure:
    """포트폴리오 비중 변화 (Stacked Area)"""
    weights_df = weights_df.dropna(how="all").fillna(0)
    fig = go.Figure()
    for col in weights_df.columns:
        fig.add_trace(
            go.Scatter(
                x=weights_df.index,
                y=weights_df[col] * 100,
                mode="lines",
                stackgroup="one",
                name=col,
            )
        )
    fig.update_layout(
        title="포트폴리오 자산별 비중 변화",
        xaxis_title="날짜",
        yaxis_title="비중 (%)",
        hovermode="x unified",
        template="plotly_white",
    )
    return fig


def plot_returns_histogram(nav: pd.Series, title: str = "수익률 분포") -> go.Figure:
    """일간 수익률 히스토그램"""
    returns = nav.pct_change().dropna() * 100
    fig = px.histogram(
        returns,
        nbins=50,
        title=title,
        labels={"value": "일간 수익륔 (%)", "count": "빈도"},
        template="plotly_white",
    )
    fig.update_layout(showlegend=False)
    return fig


def plot_trade_returns_distribution(trade_returns: pd.Series | np.ndarray, title: str = "거래별 수익률 분포") -> go.Figure:
    """Histogram + KDE + mean/median 수직선"""
    returns = np.asarray(trade_returns)
    returns = returns[np.isfinite(returns)]

    fig = go.Figure()

    # Histogram
    fig.add_trace(
        go.Histogram(
            x=returns,
            nbinsx=max(10, min(50, len(returns) // 2)),
            histnorm="density",
            name="Histogram",
            marker_color="#1f77b4",
            opacity=0.6,
        )
    )

    # KDE
    if len(returns) >= 3:
        kde = gaussian_kde(returns)
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

    # Mean line
    mean_val = np.mean(returns)
    fig.add_vline(x=mean_val, line_dash="dash", line_color="#2ca02c",
                  annotation_text="Mean", annotation_position="top")

    # Median line
    median_val = np.median(returns)
    fig.add_vline(x=median_val, line_dash="dot", line_color="#d62728",
                  annotation_text="Median", annotation_position="top right")

    fig.update_layout(
        title=title,
        xaxis_title="Trade Return (소수)",
        yaxis_title="Density",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def plot_kelly_curve(
    f_vals: np.ndarray,
    exp_log: np.ndarray,
    f_star: float | None = None,
    title: str = "켈리 기준 곡선 E[log(1+fX)]",
) -> go.Figure:
    """f에 따른 기대 로그수익 곡선"""
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
                x=f_star,
                line_dash="dash",
                line_color="#d62728",
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
        title=title,
        xaxis_title="f (Kelly Ratio)",
        yaxis_title="E[log(1 + fX)]",
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig
