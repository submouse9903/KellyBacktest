"""켈리 공식 핵심 계산 엔진

핵심 변경:
- 주식 거래에서는 평균 손실이 100%가 아니므로, discrete_kelly_adjusted를 기본으로 사용합니다.
- classical_kelly(μ/σ²) 및 discrete_kelly((bp-q)/b)는 참고용/레거시로 남겨둡니다.
"""

import numpy as np
import pandas as pd
from scipy import linalg


def _to_returns(prices: pd.Series) -> pd.Series:
    """가격 시계열을 로그수익률로 변환"""
    return np.log(prices / prices.shift(1)).dropna()


# ---------------------------------------------------------------------------
# 이산 켈리 (Discrete Kelly) - 전략 신호의 승/패 통계 기반
# ---------------------------------------------------------------------------

def discrete_kelly_adjusted(returns: pd.Series) -> float:
    """수정 이산 켈리 (주식 거래용 기본 공식)

    f* = (b*p - avg_loss*q) / (b*avg_loss)

    Args:
        returns: 각 거래별 수익률 시계열

    Returns:
        최적 켈리 비율 f*
    """
    returns = returns.dropna()
    if len(returns) < 2:
        return 0.0

    wins = returns[returns > 0]
    losses = returns[returns <= 0]

    if len(wins) == 0 or len(losses) == 0:
        return 0.0

    p = len(wins) / len(returns)
    q = 1 - p
    b = float(wins.mean())
    avg_loss = float(losses.abs().mean())

    if b == 0 or avg_loss == 0:
        return 0.0

    return float((b * p - avg_loss * q) / (b * avg_loss))


def discrete_kelly(returns: pd.Series) -> float:
    """고전 이산 켈리: f* = (bp - q) / b

    Deprecated for stock trading. 이 공식은 베팅하면 잃으면 100% 손실이라고 가정합니다.
    주식 거래에는 discrete_kelly_adjusted를 사용하세요.
    """
    returns = returns.dropna()
    if len(returns) < 2:
        return 0.0

    wins = returns[returns > 0]
    losses = returns[returns <= 0]

    if len(wins) == 0 or len(losses) == 0:
        return 0.0

    p = len(wins) / len(returns)
    q = 1 - p
    b = float(wins.mean())

    if b == 0:
        return 0.0

    return float((b * p - q) / b)


# ---------------------------------------------------------------------------
# 연속 켈리 (Continuous Kelly) - 시장 전체 수익률 분포 기반
# ---------------------------------------------------------------------------

def classical_kelly(returns: pd.Series) -> float:
    """연속 근사 켈리 공식: f* = μ / σ²

    Args:
        returns: 로그수익률 시계열

    Returns:
        최적 켈리 비율 f*
    """
    returns = returns.dropna()
    if len(returns) < 2:
        return 0.0
    mu = returns.mean()
    sigma2 = returns.var(ddof=0)
    if sigma2 == 0:
        return 0.0
    return float(mu / sigma2)


def fractional_kelly(f_star: float, fraction: float = 0.5) -> float:
    """부분 켈리 (하프켈리 등)

    Args:
        f_star: discrete_kelly_adjusted 또는 classical_kelly 결과
        fraction: 적용 비율 (0.5 = 하프켈리)

    Returns:
        조정된 켈리 비율 (음수는 0으로 클리핑)
    """
    return max(0.0, f_star * fraction)


def rolling_kelly(prices: pd.Series, window: int = 60) -> pd.Series:
    """롤링 윈도우 동적 켈리 (연속 켈리 버전)

    Args:
        prices: 가격 시계열
        window: 롤링 윈도우 크기 (영업일)

    Returns:
        시간에 따른 동적 켈리 비율
    """
    returns = _to_returns(prices)
    mu = returns.rolling(window=window, min_periods=window // 2).mean()
    sigma2 = returns.rolling(window=window, min_periods=window // 2).var(ddof=0)
    kelly = mu / sigma2
    return kelly.replace([np.inf, -np.inf], np.nan).fillna(0.0)


# ---------------------------------------------------------------------------
# 포트폴리오 (Continuous Kelly / Thorp)
# ---------------------------------------------------------------------------

def portfolio_kelly(
    returns_df: pd.DataFrame,
    risk_free_rate: float = 0.02,
    regularization: float = 1e-6,
) -> np.ndarray:
    """Thorp의 연속 켈리 포트폴리오: f* = Σ⁻¹ (μ - r)

    Args:
        returns_df: 각 자산의 로그수익률 DataFrame (columns=자산)
        risk_free_rate: 연간 무위험수익률
        regularization: 공분산 행렬의 수치적 안정성을 위한 Ridge 항

    Returns:
        각 자산별 최적 켈리 비중 배열 (shape: (n_assets,))
    """
    returns_df = returns_df.dropna()
    if returns_df.empty or returns_df.shape[1] == 0:
        return np.array([])

    mu = returns_df.mean().values * 252  # 연율화
    sigma = returns_df.cov().values * 252

    n = sigma.shape[0]
    sigma_reg = sigma + regularization * np.eye(n)

    try:
        sigma_inv = linalg.inv(sigma_reg)
    except linalg.LinAlgError:
        sigma_inv = linalg.pinv(sigma_reg)

    excess_mu = mu - risk_free_rate
    f_star = sigma_inv @ excess_mu
    return f_star


def constrained_portfolio_kelly(
    returns_df: pd.DataFrame,
    risk_free_rate: float = 0.02,
    max_leverage: float = 2.0,
    min_weight: float = -1.0,
    regularization: float = 1e-6,
) -> np.ndarray:
    """제약 조건이 추가된 포트폴리오 켈리

    Args:
        returns_df: 각 자산의 로그수익률 DataFrame
        risk_free_rate: 연간 무위험수익률
        max_leverage: 총 포지션 절대값 합의 상한
        min_weight: 개별 자산 하한 비중 (음수 = 공매도 허용)
        regularization: 수치 안정성을 위한 Ridge 항

    Returns:
        제약 조건을 반영한 각 자산별 켈리 비중
    """
    f_star = portfolio_kelly(returns_df, risk_free_rate, regularization)
    if f_star.size == 0:
        return f_star

    # 개별 하한/상한 클리핑
    f_star = np.clip(f_star, min_weight, max_leverage)

    # 총 레버리지 정규화 (선택적)
    total_abs = np.sum(np.abs(f_star))
    if total_abs > max_leverage:
        f_star = f_star * (max_leverage / total_abs)

    return f_star


# ---------------------------------------------------------------------------
# 베이지안 켈리 (옵션 / 고급)
# ---------------------------------------------------------------------------

def bayesian_kelly(
    returns: pd.Series,
    prior_mean: float = 0.0,
    prior_precision: float = 1.0,
    window: int = 60,
) -> float:
    """단순 베이지안 켈리: 사전 분포와 관측 데이터를 결합

    Args:
        returns: 로그수익률 시계열
        prior_mean: 사전 기대수익률
        prior_precision: 사전 분포의 정밀도 (역분산)
        window: 최근 관측 데이터 개수

    Returns:
        사후 분포 기반 켈리 비율
    """
    recent = returns.dropna().tail(window)
    if len(recent) < 5:
        return 0.0

    n = len(recent)
    sample_mean = recent.mean()
    sample_var = recent.var(ddof=0)

    if sample_var == 0:
        return 0.0

    # 정규-정규 사후평균
    posterior_precision = prior_precision + n / sample_var
    posterior_mean = (
        prior_precision * prior_mean + (n / sample_var) * sample_mean
    ) / posterior_precision

    return float(posterior_mean / sample_var)
