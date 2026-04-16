"""Plotly 기반 시각화 유틸리티"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_nav_comparison(nav_kelly: pd.Series, nav_buyhold: pd.Series) -> go.Figure:
    """누적 자산 곡선 비교"""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=nav_kelly.index,
            y=nav_kelly.values,
            mode="lines",
            name="Kelly Strategy",
            line=dict(color="#1f77b4", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=nav_buyhold.index,
            y=nav_buyhold.values,
            mode="lines",
            name="Buy & Hold",
            line=dict(color="#ff7f0e", width=2, dash="dot"),
        )
    )
    fig.update_layout(
        title="누적 자산 곡선 비교",
        xaxis_title="날짜",
        yaxis_title="포트폴리오 가치",
        hovermode="x unified",
        template="plotly_white",
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
