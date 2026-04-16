# HFT 관련 시리즈

> 총 8편의 글이 수집되었습니다.  
> 이 문서는 해당 시리즈의 전체 목록과 핵심 흐름을 정리한 학습 가이드입니다.

---

## 1. 개요

- **총 글 수**: 8편
- **주요 기여자**:
- 괴델: 5편
- 헤아리기: 3편
- **시간 범위**: 110831 ~ 131102

---

## 2. 글 목록 (날짜 순)

| 날짜 | 작성자 | 메뉴 | 제목 |
|:---:|:---|:---|:---|
| 110831 | 괴델 | HFT 일반 | Improving Accuracy of HFT forecasts |
| 110831 | 괴델 | HFT 일반 | [펌] 틱을 봉으로 바꿔주는 MATLAB 코드 |
| 111019 | 괴델 | HFT 일반 | HFT 기초설계 |
| 111103 | 괴델 | HFT 일반 | 돌아다니는 HFT 입문서들 |
| 111106 | 괴델 | 알고리즘 트레이딩 | CUDA with MATLAB |
| 120813 | 헤아리기 | Python Finance | [HFT by Python] JP Morgan 의 FPGA 전략 |
| 120829 | 헤아리기 | HFT 일반 | [논문] 고빈도매매(High frequency trading)와 금융시장의 질적 수준 (by 신정우) |
| 131102 | 헤아리기 | HFT 일반 | [HFT] Market Making by Dr. Sasha Stoikov |

---

## 3. 학습 포인트 및 흐름 분석

**고빈도 트레이딩(HFT)의 이론부터 하드웨어 가속까지** 다루는 시리즈입니다.

### 주요 흐름
- **이론/예측 (2011.08)**: `Improving Accuracy of HFT forecasts`, `HFT 기초이론`
- **코드/구현 (2011.08)**: `분봉으로 바꿔주는 MATLAB 코드`, `변동성콘 with MATLAB`
- **Market Making (2013.11~)**: `Market Making by Dr. Sasha Stoikov`
- **하드웨어 (2011.11~2012.08)**: `CUDA with MATLAB`, `JP Morgan의 FPGA 전략`
- **사회적 영향 (2012.08)**: `고빈도매매가 금융시장에 미치는 질적 영향`

### 핵심 학습 가이드
- HFT의 수익원은 **예측(forecasting)**과 **마켓메이킹(spread capture)**으로 양분됨
- 소프트웨어(MATLAB/Python) → GPU(CUDA) → FPGA로 이어지는 **지연시간(latency) 최적화** 단계 이해

---

> **분석일**: 2026-04-16
