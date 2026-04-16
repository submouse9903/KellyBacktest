# 켈리 백테스팅 엔진 (Strategy-Driven Kelly Backtesting Engine)

> **"전략 상태(State)를 이벤트(Event)로 변환하고, Adjusted Kelly로 최적 베팅 비중을 계산한 뒤, Next-Day Execution 원칙 하에 신호 발생 시에만 진입/청산하는"** 백테스팅 엔진입니다.

## 핵심 철학

켈리 기준은 **"언제 사느냐(Timing)"**가 아니라 **"산다면 얼마를 사느냐(Sizing)"**를 결정하는 자금관리 도구입니다.

이 엔진의 구조는 다음과 같습니다:

```
[가격 데이터]
    ↓
[Signal Engine: 상태(State) 생성]  ← +1, 0, -1 지속 구간
    ↓
[Event Extractor: 상태 변경 감지]  ← +1(진입), -1(청산), 0(유지)
    ↓
[Strategy Analyzer: 거래 수익률 추출]
    ↓
[Adjusted Kelly: f* = (bp - ql) / (bl)]  ← l = 평균 손실
    ↓
[Backtest Engine: T일 이벤트 → T+1일 실행]
```

---

## 🚀 빠른 시작

```bash
cd KellyBacktest
pip install -r requirements.txt
streamlit run app.py
```

---

## 📁 프로젝트 구조

```
KellyBacktest/
├── app.py                       # Streamlit 웹 대시보드 (4개 탭)
├── config.py                    # 거래비용, 초기자본 등 설정
├── scan_signals.py              # CLI 배치 스캐너 (Grid Search 지원)
├── src/
│   ├── signal_engine.py         # 기술적 분석 상태(State) 생성
│   ├── strategy_analyzer.py     # State→Event 변환, 수익률 추출, Grid Search, OOS
│   ├── kelly_engine.py          # Adjusted/Discrete/Continuous Kelly
│   ├── backtest_engine.py       # Event-driven Next-Day 백테스트
│   ├── metrics.py               # 성과 지표 (승률, Profit Factor, MDD 등)
│   ├── visualization.py         # Plotly 차트
│   ├── data_loader.py           # 샘플/CSV 데이터 로딩
│   └── db_connector.py          # Docker MySQL 연결
├── requirements.txt
├── README.md
├── 복붙.md                      # CLI one-liner 모음
└── 켈리베팅_백테스팅_로직.md     # 상세 아키텍처 문서
```

---

## 🎛️ 지원하는 전략 및 켈리 타입

### 전략 상태 (State → Event)
1. **Golden Cross**: 단기 MA가 장기 MA를 상향/하향 돌파한 **구간**
2. **RSI**: RSI가 과매도/과매수 구간에 진입한 **구간**
3. **Momentum Breakout**: N일 최고가/최저가를 돌파한 **구간**
4. **Bollinger Bands**: 상단/하단선을 돌파한 **구간**

> 중요: 위 신호들은 "상태(State)"를 반환합니다. 실제 거래는 **상태가 바뀌는 순간(Event)** 에만 발생합니다.

### 켈리 타입
- **Adjusted Kelly (Full)**: `f* = (bp - ql) / (bl)` — **주식 거래 기본**
- **Half Kelly**: `f* / 2`
- **Custom Fraction**: 사용자 지정 비율

> ⚠️ `f* < 0`이면 해당 전략은 **"하지 마라"**는 의미입니다. 이 경우 백테스트에서는 거래가 발생하지 않습니다.

---

## 🖥️ 웹 대시보드 사용법

### 사이드바 흐름

#### 1. 데이터 선택
- **샘플 데이터**: GBM 기반 합성 주가
- **CSV 업로드**: wide-form CSV (index=date, columns=price)
- **Docker DB**: `게만아-트레이딩`의 MySQL 컨테이너(3307)에 직접 연결

#### 2. 전략 선택
- 전략 유형 및 파라미터 설정 (MA 기간, RSI 임계값 등)
- **보유 기간(Holding Period)** 설정
- **"반대 신호 시 조기 청산"** 및 **"동일 신호 발생 시 보유 기간 연장(Renewal)"** 옵션
- **OOS 분리**: In-Sample으로 켈리 추정, Out-of-Sample으로 검증

#### 3. 켈리 설정 → 백테스트 실행
- Full / Half / Custom Kelly 선택
- **"백테스트 실행"** 버튼 클릭

### 탭 구성

| 탭 | 내용 |
|:---|:---|
| **📈 전략 분석** | 승률, 평균 수익/손실, Adjusted Kelly `f*`, OOS 결과, 가격 차트에 상태 마커 |
| **📉 백테스트 결과** | 누적 자산 곡선 (Kelly vs Buy & Hold), 일별 포지션 비중, 거래 내역 |
| **📋 성과 지표** | CAGR, MDD, Sharpe, Calmar, Profit Factor, 승률, Drawdown 차트 |
| **🔍 파라미터 최적화** | Grid Search: 여러 파라미터/보유기간 조합을 자동 탐색하여 양수 `f*` 조합 추천 |

---

## 📊 CLI 사용 예시

### 기본 분석
```bash
cd KellyBacktest
python -c "
from src import db_connector, signal_engine, strategy_analyzer, backtest_engine

# 1. 데이터
prices = db_connector.get_prices_from_db(['005930'], start_date='2020-01-01').iloc[:, 0]

# 2. 상태 → 이벤트
state = signal_engine.golden_cross(prices, 5, 20)
events = strategy_analyzer.state_to_events(state, entry_state=1)

# 3. 통계 분석
trade_returns = strategy_analyzer.extract_signal_returns(prices, events, holding_period=20)
stats = strategy_analyzer.compute_kelly_params(trade_returns)
print(f'Adjusted f* = {stats[\"f_star_adjusted\"]*100:.1f}%')

# 4. 백테스트
f = max(0.0, stats['f_star_adjusted'])
result = backtest_engine.run_strategy(prices, events, kelly_fraction=f, holding_period=20)
print(f'NAV = {result[\"nav\"].iloc[-1]:,.0f}')
"
```

### Grid Search
```bash
python scan_signals.py
```

더 많은 CLI 스크립트는 `복붙.md`를 참고하세요.

---

## 🏗️ 아키텍처 상세

### State → Event 분리

```python
# Layer 1: Signal Engine returns STATE
state = signal_engine.golden_cross(prices)  # +1, 0, -1 continuous

# Layer 2: Extract EVENTS from state changes
events = strategy_analyzer.state_to_events(state, entry_state=1)
# +1: Long Entry (state changed to +1)
# -1: Long Exit (state changed away from +1)
#  0: No event
```

이 분리의 장점:
- **Analyzer와 Backtester가 동일한 진입/청산 로직을 공유**
- 다양한 신호 엔진(Python, TA-Lib, 외부 API)을 쉽게 교체 가능
- "상태"와 "거래"의 개념적 혼란 방지

### Next-Day Execution

실제 트레이딩에서는 **종가 기준 신호를 확인하고 다음 거래일에 실행**합니다.
엔진은 이를 엄격히 따릅니다:

- **T일**: 상태 변경 감지 (Event 발생)
- **T+1일**: 진입 또는 청산 실행

이는 미래를 보는(look-ahead bias) 편향을 완전히 제거합니다.

### Adjusted Kelly

주식 거래에서는 손실이 100%가 아니므로, **고전 이산 켈리 `f* = (bp - q) / b`는 잘못된 적용**입니다.

**Adjusted Kelly (주식용)**:
\[
f^* = \frac{p \cdot b - q \cdot l}{b \cdot l}
\]

- `p`: 승률
- `q`: 1-p
- `b`: 평균 수익 (예: 0.05 = 5%)
- `l`: 평균 손실 절대값 (예: 0.03 = 3%)

예시: `p=55%`, `b=5%`, `l=3%`
- 고전 켈리: `(0.05*0.55 - 0.45) / 0.05 = -8.45` → **음수, 버림**
- Adjusted: `(0.05*0.55 - 0.03*0.45) / (0.05*0.03) = +9.33` → **양수**

### Holding Period Renewal

추세 추종 전략에서 같은 방향의 상태가 지속되면, 중간에 **새로운 Entry Event가 발생**할 수 있습니다.
(예: Golden Cross가 50일 유지되다가 51일째 다시 crossover → 연속 진입)

이때 엔진은 기존 포지션을 유지하면서 **보유 기간을 현재 시점부터 다시 연장**합니다.

### OOS (Out-of-Sample) 검증

과거 데이터 전체로 `f*`를 추정하고 동일 데이터로 백테스트하면 **과적합(Overfitting)** 문제가 생깁니다.

엔진은 데이터를 **In-Sample / Out-of-Sample**로 분리합니다:
1. **IS (70%)**: `p`, `b`, `l`을 추정하여 `f*`를 계산
2. **OOS (30%)**: IS에서 계산한 `f*`를 고정하여 백테스트

OOS에서도 `f* > 0`이어야 비로소 "신뢰할 만한 전략"으로 판단할 수 있습니다.

---

## ⚠️ 주의사항

### Adjusted Kelly의 민감성
`f* = (bp - ql) / (bl)`은 `b`와 `l`의 비율에 따라 민감하게 변동합니다.

**엔진의 처리 방식:**
- `f* < 0` → **전략에 엣지가 없음**, 백테스트에서 거래하지 않음
- `f* > 0`이더라도 **Half Kelly(50%)** 이하를 사용하는 것을 권장
- 거래 횟수가 30회 미만이면 통계적으로 신뢰하기 어려움

### 켈리 공식 비교
| 구분 | 공식 | 사용처 |
|:---|:---|:---|
| **Adjusted Kelly** | `f* = (bp - ql) / (bl)` | 주식/선물 거래 (부분 손실/수익) — **기본** |
| **Discrete Kelly** | `f* = (bp - q) / b` | 올인/올아웃 베팅 (잃으면 100% 손실) |
| **Continuous Kelly** | `f* = μ / σ²` | 연속적 포트폴리오 리밸런싱 (고급) |

---

## 기대 효과

- `f* > 0` → "이 전략은 유리하다, 이 비중으로 베팅하라"
- `f* <= 0` → "이 전략은 기대값이 음수이거나 없다, 하지 마라"
- **State/Event 분리**로 신호 엔진과 백테스터의 일관성 확보
- **OOS + Grid Search**로 과적합 방지 및 실전 적용 가능한 엣지 탐색

---

> **기준 이론**: Edward Thorp의 연속 켈리, 큐래프트 카페 `켈리기준 자금관리` 시리즈  
> **제작일**: 2026-04-16
