"""성과 지표 계산 모듈"""

import numpy as np
import pandas as pd


def total_return(nav: pd.Series) -> float:
    """총 수익률"""
    return float(nav.iloc[-1] / nav.iloc[0] - 1)


def cagr(nav: pd.Series) -> float:
    """연평균 복리수익률 (CAGR)"""
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    if years <= 0:
        return 0.0
    return float((nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1)


def volatility(nav: pd.Series, annualize: bool = True) -> float:
    """수익률 변동성 (표준편차)"""
    returns = nav.pct_change().dropna()
    vol = returns.std(ddof=1)
    if annualize:
        vol *= np.sqrt(252)
    return float(vol)


def sharpe_ratio(nav: pd.Series, risk_free: float = 0.02) -> float:
    """샤프 비율"""
    returns = nav.pct_change().dropna()
    if returns.empty:
        return 0.0
    excess = returns.mean() * 252 - risk_free
    vol = returns.std(ddof=1) * np.sqrt(252)
    if vol == 0:
        return 0.0
    return float(excess / vol)


def max_drawdown(nav: pd.Series) -> float:
    """최대 낙폭 (Maximum Drawdown)"""
    cummax = nav.cummax()
    drawdown = (nav - cummax) / cummax
    return float(drawdown.min())


def calmar_ratio(nav: pd.Series) -> float:
    """칼마 비율 (CAGR / |MDD|)"""
    c = cagr(nav)
    mdd = max_drawdown(nav)
    if mdd == 0:
        return 0.0
    return float(c / abs(mdd))


# ---------------------------------------------------------------------------
# 거래 기반 지표
# ---------------------------------------------------------------------------

def win_rate(trade_returns: pd.Series) -> float:
    """승률"""
    returns = trade_returns.dropna()
    if len(returns) == 0:
        return 0.0
    return float((returns > 0).mean())


def avg_win(trade_returns: pd.Series) -> float:
    """평균 수익"""
    wins = trade_returns[trade_returns > 0]
    return float(wins.mean()) if len(wins) > 0 else 0.0


def avg_loss(trade_returns: pd.Series) -> float:
    """평균 손실 (절대값)"""
    losses = trade_returns[trade_returns <= 0]
    return float(losses.abs().mean()) if len(losses) > 0 else 0.0


def profit_factor(trade_returns: pd.Series) -> float:
    """Profit Factor = 총 수익 / 총 손실 절대값"""
    returns = trade_returns.dropna()
    if len(returns) == 0:
        return 0.0
    total_wins = returns[returns > 0].sum()
    total_losses = returns[returns <= 0].abs().sum()
    if total_losses == 0:
        return float('inf') if total_wins > 0 else 0.0
    return float(total_wins / total_losses)


def kelly_expected_growth(f_star: float, p: float, b: float, q: float, avg_loss: float = 1.0) -> float:
    """켈리 베팅 비중 f* 하에서의 기대 로그 성장률

    G(f) = p * log(1 + b*f) + q * log(1 - avg_loss*f)

    Args:
        f_star: 켈리 비중
        p: 승률
        b: 평균 수익
        q: 패배 확률
        avg_loss: 평균 손실 절대값 (기본 1.0 = 고전 켈리)
    """
    if f_star <= 0 or b <= 0 or avg_loss <= 0:
        return 0.0
    growth = p * np.log(1 + b * f_star) + q * np.log(1 - avg_loss * f_star)
    return float(growth)


# ---------------------------------------------------------------------------
# 종합 리포트
# ---------------------------------------------------------------------------

def generate_report(nav: pd.Series, name: str = "Strategy") -> pd.DataFrame:
    """종합 성과 리포트 생성 (DataFrame 형태)"""
    data = {
        "지표": ["총수익률", "CAGR", "변동성(연)", "샤프비율", "최대낙폭(MDD)", "칼마비율"],
        name: [
            f"{total_return(nav)*100:.2f}%",
            f"{cagr(nav)*100:.2f}%",
            f"{volatility(nav)*100:.2f}%",
            f"{sharpe_ratio(nav):.3f}",
            f"{max_drawdown(nav)*100:.2f}%",
            f"{calmar_ratio(nav):.3f}",
        ],
    }
    return pd.DataFrame(data)


def generate_trade_report(trade_returns: pd.Series, name: str = "Trades") -> pd.DataFrame:
    """거래별 성과 리포트"""
    returns = trade_returns.dropna()
    if len(returns) == 0:
        return pd.DataFrame({"지표": ["거래수", "승률", "평균수익", "평균손실", "Profit Factor"], name: ["0", "0.0%", "0.0%", "0.0%", "0.000"]})

    data = {
        "지표": ["거래수", "승률", "평균수익", "평균손실", "Profit Factor"],
        name: [
            f"{len(returns)}",
            f"{win_rate(returns)*100:.1f}%",
            f"{avg_win(returns)*100:.2f}%",
            f"{avg_loss(returns)*100:.2f}%",
            f"{profit_factor(returns):.3f}",
        ],
    }
    return pd.DataFrame(data)
