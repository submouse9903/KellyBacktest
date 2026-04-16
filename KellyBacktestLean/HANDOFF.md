# 다음 에이전트용 핸드오프 문서

> **작업 배경**: `KellyBacktest`(Python Pandas+Streamlit 기반 켈리 백테스팅 엔진)를 **QuantConnect Lean(Docker)** 환경으로 마이그레이션하는 작업이다.
> **현재 상태**: 핵심 아키텍처 구축 및 통합 테스트 통과 완료. Lean이 KRX 데이터를 읽고 거래를 실행하는 것까지 검증됨.

---

## 1. 완료된 핵심 작업

### 1.1 데이터 파이프라인
- `scripts/export_lean_data.py`: MySQL(`trading` DB, port 3307)에서 KRX 일봉 종가를 조회하여 Lean이 읽을 수 있는 CSV로 변환한다.
- 출력 경로: `data/equity/usa/daily/{symbol}.csv`
- CSV 포맷: `date,open,high,low,close,volume` (헤더 포함, `yyyy-MM-dd` 날짜 포맷)
- **핵심 제약**: KRX 데이터가 Lean 표준 `Equity` 모델과 100% 호환되지 않아 **Custom Data Source**를 사용한다.

### 1.2 Lean Python Algorithm
- `lean-algo/main.py`: `QCAlgorithm`을 상속한 `KellySignalAlgorithm` 클래스.
- `KrxDailyData(PythonData)`: CSV를 직접 파싱하여 Lean에 공급하는 커스텀 데이터 소스.
- 주요 기능 구현 완료:
  - **Next-Day Execution**: T일 신호 → T+1일 거래
  - **State → Event**: 상태 변경 순간만 이벤트로 감지
  - **Holding Period + Renewal**: 동일 방향 이벤트 발생 시 보유 기간 연장
  - **Kelly Sizing**: `cash * kelly_fraction`만큼 투자
  - **Short 포지션**: `direction="short"` 시 음수 수량으로 공매도
  - **거래비용**: `CustomFeeModel`(0.15%) + `CustomSlippageModel`(0.05%)
- 결과물: `results/kelly_results.json` (trade_log, nav_history, position_history, final_nav, cagr, mdd, total_return)

### 1.3 실행 환경
- `scripts/docker_run.ps1`: Windows PowerShell용 Lean Docker 실행 스크립트
- `lean-algo/lean_launcher_config.json`: Lean Launcher 설정 (algorithm-location, data-folder, results-destination 등)
- Docker 마운트:
  - `lean-algo` → `/Lean/Launcher/bin/Debug/Algorithms`
  - `data` → `/Data`
  - `results` → `/Results`

### 1.4 메타데이터 보강
Lean 컨테이너 낸부에 `/Data`가 원래 없으므로, 다음 메타데이터를 수동으로 다운로드/생성하여 `data/` 아래에 배치했다:
- `data/symbol-properties/symbol-properties-database.csv` (GitHub QuantConnect/Lean에서 다운로드)
- `data/market-hours/market-hours-database.json` (GitHub에서 다운로드)
- `data/equity/usa/map_files/{symbol}.txt` (심볼별로 생성 필요)
- `data/equity/usa/factor_files/` (빈 폴터, warning 방지)

> **다음 에이전트 참고**: 새로운 심볼을 추가할 때는 반드시 해당 심볼의 `map_files/{symbol}.txt`도 함께 생성해야 Lean이 데이터를 인식한다.

### 1.5 오케스트레이터
- `orchestrator/run_single_backtest.py`: 1개 config로 Lean Docker 실행 → `results/kelly_results.json` 반환
- `orchestrator/run_grid_search.py`:
  - Pandas로 IS 분석 (state → events → trade_returns → f_star_adjusted 계산)
  - `f_star_adjusted > 0`이고 `n_trades >= min_trades`인 조합에 대해서만 Lean 백테스트 실행
  - 결과를 `results/grid_search_results.csv`에 저장
  - **현재 `run_lean=False`로 기본 설정되어 있음** (안전을 위해). 실제 Lean 실행하려면 이 플래그를 `True`로 바꿔야 한다.
- `orchestrator/run_oos.py`:
  - 데이터를 70/30으로 분리
  - IS에서 `f*` 추정 → OOS 기간에 Lean 백테스트 실행
  - `results/oos_summary.json`에 비교 결과 저장

### 1.6 리포팅 및 시각화
- `report/parse_lean_results.py`: Lean JSON 결과를 파싱하여 CAGR, MDD, Sharpe, total return 등을 계산
- `report/report.py`: 정적 HTML 리포트 생성 (`--input`, `--output` CLI 지원)
- `report/dashboard.py`: Streamlit 앱 (Lean 결과 JSON 또는 Grid Search CSV 업로드/선택 가능)

### 1.7 통합 테스트
- `tests/test_integration.py`: 완전한 End-to-End 테스트
- 합성 데이터(`SAMPLE`)를 생성하여 Lean Docker를 실제로 실행(또는 Docker 없으면 mock fallback)
- **테스트 결과: 4/4 통과**, Lean이 201개 데이터 포인트를 처리하고 12개 주문(6개 완결 거래)를 생성함을 검증

---

## 2. 남은 작업 / 다음 에이전트가 할 수 있는 일

### 우선순위 높음
1. **실제 KRX 데이터로 End-to-End 테스트**
   - `python scripts/export_lean_data.py`를 실행하여 `005930` 등 실제 종목 데이터를 생성
   - `lean-algo/config.json`에 해당 종목을 설정하고 `scripts/docker_run.ps1`로 단일 백테스트 실행
   - 결과 JSON이 정상적으로 생성되는지, 거래가 실제로 발생하는지 확인

2. **Grid Search 실전 운용**
   - `orchestrator/run_grid_search.py`에서 `run_lean=True`로 전환
   - 005930을 대상으로 Golden Cross Grid Search를 실제 실행
   - 실행 속도가 느리면 병렬화(멀티프로세싱) 또는 샘플링 전략 고려

3. **Map 파일 자동 생성**
   - 현재는 수동으로 `map_files/{symbol}.txt`를 만들어야 한다.
   - `export_lean_data.py`에 심볼 추가 시 map 파일도 자동으로 생성하는 로직을 추가하면 좋다.

### 우선순위 중간
4. **OOS 시각화 강화**
   - `run_oos.py`의 결과(`oos_summary.json`)를 읽어 IS NAV 곡선 vs OOS NAV 곡선을 비교하는 차트 추가
   - `report.py` 또는 `dashboard.py`에 OOS 전용 탭/섹션 추가

5. **Streamlit 대시보드 고도화**
   - `dashboard.py`의 4개 탭(Strategy Analysis, Backtest Results, Performance Metrics, Grid Search Results)을 실제 Lean 출력에 맞게 세부 구현
   - Plotly 차트(NAV vs Buy&Hold, Drawdown, Position Weight, Trade Histogram) 추가

6. **Interest Rate Warning 해소**
   - Lean 로그에 `/Data/alternative/interest-rate/usa/interest-rate.csv` 부재 warning이 뜬다.
   - 실행에는 지장 없지만, 깔끔하게 하려면 GitHub Lean repo에서 해당 파일을 다운로드하여 `data/alternative/interest-rate/usa/`에 배치

### 우선순위 낮음 / 고급
7. **추가 전략 안정성 테스트**
   - `main.py`에는 Golden Cross, RSI, Momentum Breakout, Bollinger Bands가 모두 구현되어 있지만, 통합 테스트는 Golden Cross 위주로 진행됨
   - 나머지 3개 전략도 샘플 데이터로 Lean 백테스트하여 이상 유무 확인

8. **docker-compose.yml 작성**
   - 현재는 PowerShell 스크립트로 Docker를 실행하지만, `docker-compose.yml`로 표준화하면 CI/CD 연동이 쉬워진다.

9. **Buy & Hold 벤치마크 추가**
   - 현재 Lean 알고리즘 결과에는 Kelly Strategy NAV만 있고 Buy & Hold 비교 곡선이 없다.
   - `main.py`에 초기 자본으로 첫 거래일에 100% 매수하고 끝까지 보유하는 벤치마크 로직 추가
   - `report.py`의 차트에서 두 곡선을 오버레이 비교

---

## 3. 알려진 이슈 및 우회책

| 이슈 | 상태 | 우회책 |
|:---|:---|:---|
| Lean 표준 Equity 모델이 KRX CSV를 읽지 못함 | **해결** | `KrxDailyData(PythonData)` 커스텀 데이터 소스 사용 |
| `/Data` 디렉토리 부재로 symbol-properties 오류 | **해결** | GitHub에서 메타데이터 다운로드 후 `data/`에 마운트 |
| `map_files` 부재로 데이터 인식 실패 | **해결** | 심볼별 `.txt` map 파일 수동 생성 |
| `factor_files` 부재 warning | **해결** | 빈 폴터 생성 |
| `interest-rate.csv` 부재 warning | 미해결 | 실행에는 무관, 선택적으로 파일 추가 가능 |
| `self.end_date`가 QCAlgorithm 속성과 충돌 | **해결** | `self._algo_end_date`로 변수명 변경 |
| CSV vs ZIP 포맷 혼란 | **해결** | Custom Data Source에서는 **CSV 직접 읽기**로 확정 |

---

## 4. 실행 체크리스트 (다음 에이전트용)

```powershell
# 1. 환경 확인
cd KellyBacktestLean
docker images | findstr quantconnect/lean

# 2. Python 의존성 확인
pip install -r requirements.txt

# 3. 통합 테스트 (Docker 유무에 따라 mock 또는 실제 실행)
python tests/test_integration.py
# → 4개 테스트 모두 OK 나와야 함

# 4. 실제 데이터 납품 (MySQL이 켜져 있어야 함)
python scripts/export_lean_data.py

# 5. 단일 백테스트
# 먼저 lean-algo/config.json을 원하는 심볼/전략으로 수정
.\scripts\docker_run.ps1
# → results/kelly_results.json 생성 확인

# 6. 결과 파싱
python -c "from report.parse_lean_results import load_results, compute_metrics; d=load_results('results/kelly_results.json'); print(compute_metrics(d['nav_history']))"

# 7. Grid Search (run_lean=True로 전환 후)
python orchestrator/run_grid_search.py

# 8. OOS
python orchestrator/run_oos.py

# 9. 리포트
python report/report.py --input results/kelly_results.json --output results/report.html
```

---

## 5. 디렉토리 및 파일 빠른 참조

```
KellyBacktestLean/
├── data/                              ← Lean이 읽는 데이터 + 메타데이터
│   ├── equity/usa/daily/              ← {symbol}.csv (Custom Data Source)
│   ├── equity/usa/map_files/          ← {symbol}.txt (필수)
│   ├── equity/usa/factor_files/       ← (빈 폴터)
│   ├── market-hours/
│   └── symbol-properties/
├── lean-algo/                         ← Lean Python Algorithm
│   ├── main.py                        ← KellySignalAlgorithm + KrxDailyData
│   ├── lean_signals.py                ← TA indicators (no pandas)
│   ├── lean_kelly.py                  ← Kelly math (no pandas)
│   ├── lean_utils.py                  ← Fee/Slippage models
│   ├── config.json                    ← 알고리즘 파라미터
│   └── lean_launcher_config.json      ← Lean 실행 설정
├── orchestrator/                      ← Python 메타 오케스트레이터
│   ├── run_single_backtest.py
│   ├── run_grid_search.py             ← run_lean=False 기본값
│   └── run_oos.py
├── report/                            ← 결과 시각화
│   ├── parse_lean_results.py
│   ├── report.py
│   └── dashboard.py
├── scripts/                           ← 유틸리티
│   ├── export_lean_data.py
│   └── docker_run.ps1
├── tests/
│   └── test_integration.py            ← 통과 완료
├── requirements.txt
├── README.md
└── HANDOFF.md                         ← 이 문서
```

---

## 6. 중요한 코드 조각

### Custom Data Source (main.py)
```python
class KrxDailyData(PythonData):
    def GetSource(self, config, date, isLiveMode):
        path = f"/Data/equity/usa/daily/{config.Symbol.Value.lower()}.csv"
        return SubscriptionDataSource(path, SubscriptionTransportMedium.LocalFile)

    def Reader(self, config, line, date, isLiveMode):
        if not line or line.strip() == "" or line.startswith("date"):
            return None
        parts = line.split(",")
        dt = datetime.strptime(parts[0].strip(), "%Y-%m-%d") + timedelta(hours=6, minutes=30)
        # ... data 설정 후 return
```

### Next-Day Execution 패턴 (main.py OnData)
```python
# event는 오늘 상태 변경으로 계산됨
# yesterday_event는 어제 계산해서 저장핸 값
if not self.in_position and self.yesterday_event == 1:
    self._execute_entry(price)
if self.in_position and self.yesterday_event == -1:
    self._execute_exit(price, "opposite_signal")
self.yesterday_event = event  # 오늘 event를 내일 사용
```

---

## 7. 연락/문맥

- 이 프로젝트는 **Option A: Lean Native + Python Orchestrator** 접근법으로 승인되어 실행되었다.
- 기존 `KellyBacktest/` 디렉토리는 참조용으로 남아 있으며, 새로운 Lean 기반 구현은 `KellyBacktestLean/`에 모두 있다.
- 모든 파일은 Windows 환경에서 작성 및 테스트되었으며, PowerShell 경로(`Resolve-Path`)를 사용한다.
