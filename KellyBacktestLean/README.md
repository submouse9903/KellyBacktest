# KellyBacktestLean

**KellyBacktest → QuantConnect Lean 마이그레이션 프로젝트**

기존 Python(Pandas + Streamlit) 기반의 **신호 기반 켈리 자금관리 백테스팅 엔진**을 **QuantConnect Lean(Docker)** 환경으로 완전히 이식한 프로젝트입니다.

## 핵심 철학

- **State → Event 분리**: 신호 엔진은 +1/0/-1 "상태"를 반환하고, 상태 변경 순간만 "이벤트"로 취급합니다.
- **Next-Day Execution**: T일 종가 기준 신호 → T+1일 오전 개장 시 실행 (look-ahead bias 제거)
- **Adjusted Kelly**: `f* = (bp - ql) / (bl)`로 주식 거래에 맞는 켈리 비중 계산
- **Grid Search + OOS**: Python 오케스트레이터가 Lean을 반복 호출하여 파라미터 최적화 및 Out-of-Sample 검증 수행

---

## 프로젝트 구조

```
KellyBacktestLean/
├── data/                              # Lean Local Data + 메타데이터
│   ├── equity/usa/daily/              # 일별 OHLCV CSV (Custom Data Source)
│   ├── equity/usa/map_files/          # 심볼 매핑 파일
│   ├── equity/usa/factor_files/       # (빈 폴터)
│   ├── market-hours/                  # Lean 기본 메타데이터
│   └── symbol-properties/             # Lean 기본 메타데이터
├── lean-algo/                         # Lean Python Algorithm
│   ├── main.py                        # KellySignalAlgorithm (KrxDailyData Custom Source)
│   ├── lean_signals.py                # RollingWindow 기반 TA 신호
│   ├── lean_kelly.py                  # Discrete Kelly (adjusted)
│   ├── lean_utils.py                  # FeeModel / SlippageModel / JSON 저장
│   ├── config.json                    # 알고리즘 파라미터 템플릿
│   └── lean_launcher_config.json      # Lean Launcher 설정
├── orchestrator/                      # 메타 오케스트레이터
│   ├── run_single_backtest.py         # 1회 Lean Docker 실행
│   ├── run_grid_search.py             # Grid Search (Pandas IS 필터링 + Lean OOS)
│   └── run_oos.py                     # Out-of-Sample 워크플로우
├── report/                            # 결과 시각화
│   ├── parse_lean_results.py          # Lean JSON 파싱 및 metrics 계산
│   ├── report.py                      # 정적 HTML 리포트 생성
│   └── dashboard.py                   # Streamlit 결과 대시보드
├── scripts/                           # 유틸리티
│   ├── export_lean_data.py            # MySQL → Lean CSV 변환
│   └── docker_run.ps1                 # Windows PowerShell Docker 실행기
├── tests/
│   └── test_integration.py            # End-to-end 통합 테스트
└── requirements.txt
```

---

## 사전 준비

1. **Docker**가 설치되어 있고 `quantconnect/lean:latest` 이미지가 있어야 합니다.
2. (선택) KRX 데이터를 MySQL(`trading` DB, port 3307)에서 가져오려면 해당 Docker 컨테이너가 실행 중이어야 합니다.
3. Python 패키지 설치:

```powershell
cd KellyBacktestLean
pip install -r requirements.txt
```

---

## 1. 데이터 납품 (DB → Lean)

```powershell
python scripts/export_lean_data.py
```

- `KellyBacktest/src/db_connector.py`의 설정을 재사용하여 MySQL에서 KRX 일봉 데이터를 조회합니다.
- `data/equity/usa/daily/{symbol}.csv` 형태로 저장됩니다 (Custom Data Source 포맷).

---

## 2. 단일 백테스트 실행

### PowerShell 스크립트로 실행

```powershell
.\scripts\docker_run.ps1
```

- 실행 전 `lean-algo/config.json`에 원하는 파라미터를 설정하세요.
- 결과는 `results/kelly_results.json`에 저장됩니다.

### config.json 예시

```json
{
  "symbol": "005930",
  "signal_name": "golden_cross",
  "short": 5,
  "long": 20,
  "holding_period": 20,
  "kelly_fraction": 0.25,
  "direction": "long",
  "exit_on_opposite": true,
  "allow_renewal": true,
  "initial_cash": 1000000,
  "start_date": "2020-01-01",
  "end_date": "2024-12-31"
}
```

---

## 3. Grid Search

```powershell
python orchestrator/run_grid_search.py
```

- `run_grid_search.py` 낸부의 `run_lean=False`를 `True`로 바꾸면 qualifying 조합에 대해 실제 Lean 백테스트가 수행됩니다.
- 결과는 `results/grid_search_results.csv`에 저장됩니다.

---

## 4. Out-of-Sample (OOS)

```powershell
python orchestrator/run_oos.py
```

- IS(70%) 기간으로 `f*`를 추정한 뒤, OOS(30%) 기간에 대해 Lean 백테스트를 실행합니다.
- 비교 결과는 `results/oos_summary.json`에 저장됩니다.

---

## 5. 결과 리포팅

### 정적 HTML 리포트

```powershell
python report/report.py --input results/kelly_results.json --output results/report.html
```

### Streamlit 대시보드

```powershell
streamlit run report/dashboard.py
```

---

## 6. 통합 테스트

```powershell
python tests/test_integration.py
```

- Docker가 있으면 실제 Lean 백테스트를 실행하고, 없으면 mock 결과로 테스트합니다.
- 위 명령을 실행하면 `data/equity/usa/daily/SAMPLE.csv`가 생성되고 Lean이 201개의 데이터 포인트를 처리하여 몇 개의 거래를 생성하는지 검증합니다.

---

## 주의사항 및 제약

- **KRX 데이터는 Lean 표준 Equity 모델과 100% 호환되지 않습니다.** 따라서 `KrxDailyData(PythonData)`라는 **Custom Data Source**를 사용하여 CSV를 직접 파싱합니다.
- **Slippage/Commission**: `CustomFeeModel`과 `CustomSlippageModel`로 `0.15%` 수수료 + `0.05%` 슬리피지를 반영합니다.
- **Short 포지션**: `direction: "short"` 설정 시 음수 quantity로 공매도를 시뮬레이션합니다.
- **Holding Period Renewal**: 동일 방향 이벤트 발생 시 보유 기간이 현재 시점부터 다시 연장됩니다.

---

## 기여 및 라이선스

이 프로젝트는 큐래프트 카페 `켈리기준 자금관리` 시리즈를 기반으로 작성되었습니다.
