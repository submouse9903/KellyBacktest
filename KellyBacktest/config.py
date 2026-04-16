"""켈리 백테스팅 엔진 기본 설정"""

from pathlib import Path

# 프로젝트 루트
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"

# 백테스팅 기본 설정
INITIAL_CASH = 1_000_000
RISK_FREE_RATE = 0.02  # 연간 무위험수익률

# 거래비용 (%)
COMMISSION_RATE = 0.0015  # 수수료 0.15%
SLIPPAGE_RATE = 0.0005    # 슬리피지 0.05%

# 리밸런싱 주기 매핑
REBALANCE_MAP = {
    "D": "일간",
    "W": "주간",
    "M": "월간",
    "Q": "분기",
}

# 샘플 데이터 기본 파라미터
SAMPLE_YEARS = 5
SAMPLE_DAYS_PER_YEAR = 252
SAMPLE_SEED = 42

# 켈리 엔진 기본값
DEFAULT_KELLY_WINDOW = 60  # 롤링 켈리 윈도우 (영업일 기준)
MAX_LEVERAGE = 2.0         # 최대 레버리지 배수
MIN_KELLY_FRACTION = 0.0   # 최소 켈리 비율 하한
