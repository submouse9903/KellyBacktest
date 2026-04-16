"""데이터 로딩 및 샘플 데이터 생성 모듈"""

from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd


def load_csv(
    file_path: Union[str, Path],
    date_col: str = "date",
    price_col: str = "close",
    wide_form: bool = False,
) -> Union[pd.Series, pd.DataFrame]:
    """CSV 파일을 로드하여 표준 형식으로 변환

    Args:
        file_path: CSV 파일 경로
        date_col: 날짜 컬럼명 (wide_form=False 일 때)
        price_col: 가격 컬럼명 (wide_form=False 일 때)
        wide_form: wide-form CSV인지 여부 (index=date, columns=ticker)

    Returns:
        단일 종목: pd.Series (index=date, name=ticker)
        다중 종목: pd.DataFrame (index=date, columns=ticker)
    """
    df = pd.read_csv(file_path)

    if wide_form:
        df.index = pd.to_datetime(df.iloc[:, 0])
        df = df.iloc[:, 1:]
        return df.sort_index()

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col).set_index(date_col)

    # 단일 티커인지 확인
    if df.shape[1] == 1:
        return df.iloc[:, 0]
    return df


def validate_data(df: Union[pd.Series, pd.DataFrame]) -> Union[pd.Series, pd.DataFrame]:
    """결측치 및 날짜 누락 검증 및 보간

    Args:
        df: 가격 시계열

    Returns:
        보간 및 정제된 시계열
    """
    if isinstance(df, pd.Series):
        df = df.copy()
    else:
        df = df.copy()

    # 결측치 보간 (선형)
    df = df.interpolate(method="linear")
    # 앞뒤 결측치는 forward/backward fill
    df = df.ffill().bfill()

    # 음수 또는 0 가격 체크
    if (df <= 0).any().any():
        raise ValueError("가격 데이터에 0 또는 음수가 포함되어 있습니다.")

    return df


def generate_sample_data(
    ticker: str = "SAMPLE",
    years: int = 5,
    mu: float = 0.10,
    sigma: float = 0.20,
    seed: int = 42,
    days_per_year: int = 252,
) -> pd.Series:
    """기하브라운욏동(GBM) 샘플 데이터 생성

    Args:
        ticker: 티커명
        years: 생성할 연수
        mu: 연간 기대수익률
        sigma: 연간 변동성
        seed: 난수 시드
        days_per_year: 1년 영업일 수

    Returns:
        일별 종가 시계열 (pd.Series)
    """
    rng = np.random.default_rng(seed)
    n_days = years * days_per_year
    dt = 1 / days_per_year

    # 날짜 인덱스 생성 (영업일 기준)
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n_days)

    # GBM 경로 생성
    returns = rng.normal(loc=mu * dt, scale=sigma * np.sqrt(dt), size=n_days)
    price_path = 100 * np.exp(np.cumsum(returns))

    return pd.Series(price_path, index=dates, name=ticker)


def generate_multi_asset_data(
    tickers: list[str],
    years: int = 5,
    mu_vec: np.ndarray = None,
    cov_matrix: np.ndarray = None,
    seed: int = 42,
    days_per_year: int = 252,
) -> pd.DataFrame:
    """다중 자산 GBM 샘플 데이터 생성

    Args:
        tickers: 자산 이름 리스트
        years: 생성할 연수
        mu_vec: 연간 기대수익률 벡터 (n,)
        cov_matrix: 연간 공분산 행렬 (n, n)
        seed: 난수 시드
        days_per_year: 1년 영업일 수

    Returns:
        일별 종가 DataFrame (index=date, columns=ticker)
    """
    n_assets = len(tickers)
    rng = np.random.default_rng(seed)
    n_days = years * days_per_year
    dt = 1 / days_per_year

    if mu_vec is None:
        mu_vec = np.array([0.08, 0.12, 0.10, 0.06][:n_assets])
    if cov_matrix is None:
        # 간단한 상관관계 구조 생성
        base_corr = 0.3
        cov_matrix = np.full((n_assets, n_assets), base_corr)
        np.fill_diagonal(cov_matrix, 1.0)
        # 변동성 15%~25% 가정
        vols = np.linspace(0.15, 0.25, n_assets)
        cov_matrix = np.diag(vols) @ cov_matrix @ np.diag(vols)

    mu_vec = np.asarray(mu_vec)
    cov_matrix = np.asarray(cov_matrix)

    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n_days)

    # 다변량 정규분포로 수익률 생성
    returns = rng.multivariate_normal(
        mean=mu_vec * dt,
        cov=cov_matrix * dt,
        size=n_days,
    )

    price_paths = 100 * np.exp(np.cumsum(returns, axis=0))
    return pd.DataFrame(price_paths, index=dates, columns=tickers)
