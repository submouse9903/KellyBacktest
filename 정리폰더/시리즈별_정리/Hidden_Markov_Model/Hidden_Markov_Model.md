# Hidden Markov Model 시리즈

> 총 6편의 글이 수집되었습니다.  
> 이 문서는 해당 시리즈의 전체 목록과 핵심 흐름을 정리한 학습 가이드입니다.

---

## 1. 개요

- **총 글 수**: 6편
- **주요 기여자**:
- 괴델: 6편
- **시간 범위**: 070204 ~ 110509

---

## 2. 글 목록 (날짜 순)

| 날짜 | 작성자 | 메뉴 | 제목 |
|:---:|:---|:---|:---|
| 070204 | 괴델 | data_HMM | Markov Chain Monte Carlo Method Tutorial |
| 080222 | 괴델 | 자유로운 글 | 르네상스테크놀로지스의 성배: HMM 모델을 선택해야하는 이유 |
| 080223 | 괴델 | data_HMM | A Tutorial on Hidden Markov Models and Selected Applications in Speech Recognition |
| 110508 | 괴델 | data_HMM | HMM기초[펌] |
| 110508 | 괴델 | data_HMM | MM 퍼온글 |
| 110509 | 괴델 | data_HMM | Hierarchical Hidden Markov Model of High-Frequency Market Regimes Using Trade Price and Limit Order Book Information |

---

## 3. 학습 포인트 및 흐름 분석

**금융 시장의 체제 변환(regime switching)을 모델링하는 HMM** 관련 자료 모음입니다.

### 주요 흐름
- **기초 (2007.02)**: `Markov Chain Monte Carlo Method Tutorial`
- **고급 응용 (2008.02~2011.05)**: `A Tutorial on Hidden Markov Models`(Rabiner 원문), `Hierarchical Hidden Markov Model of High-Frequency Market Regimes`
- **실전 연결 (2008.02)**: `륜에상스가 HMM을 선택해야 하는 이유`

### 핵심 학습 가이드
- Rabiner의 `A Tutorial on Hidden Markov Models`은 음성인식 분야의 고전이지만, 금융 시장의 체제 변환 모델링에 직접 적용 가능
- HMM은 추세/횡보장 같은 **잠재 상태(latent state)**를 추론하는 데 탁월

---

> **분석일**: 2026-04-16
