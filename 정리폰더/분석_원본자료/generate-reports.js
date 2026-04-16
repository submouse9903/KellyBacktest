const fs = require('fs');
const path = require('path');

const posts = JSON.parse(fs.readFileSync('posts-data.json', 'utf8'));

fs.mkdirSync('큐래프트 스크래핑/시리즈별_정리', { recursive: true });
fs.mkdirSync('큐래프트 스크래핑/연도별_정리', { recursive: true });

const seriesDefs = [
  { id: '켈리기준_자금관리', name: '켈리기준 자금관리 시리즈', test: t => t.includes('켈리') || t.includes('Kelly') || t.includes('kelly') || t.includes('자금관리') },
  { id: 'Statistical_Arbitrage', name: 'Statistical Arbitrage 시리즈', test: t => t.includes('Statistical Arbitrage') || t.includes('statistical arbitrage') || t.includes('Arbitraging Arbitrageurs') },
  { id: 'Global_Momentum', name: 'Global Momentum 성과 공유', test: t => t.includes('Global Momentum') || (t.includes('공유') && t.includes('성과')) || (t.includes('성과') && t.includes('크래프트')) },
  { id: 'Python_Finance', name: 'Python Finance 시리즈', test: t => t.includes('Python Finance') },
  { id: 'HFT', name: 'HFT 관련 시리즈', test: t => t.includes('HFT') || t.includes('고빈도') || t.includes('high frequency') || t.includes('FPGA') || t.includes('CUDA') },
  { id: 'Hidden_Markov_Model', name: 'Hidden Markov Model 시리즈', test: t => t.includes('HMM') || t.includes('Markov') || t.includes('markov') },
  { id: 'Jim_Simons', name: 'Jim Simons / 륜에상스 시리즈', test: t => t.includes('Simons') || t.includes('simons') || t.includes('Renaissance') || t.includes('륜에상스') },
  { id: '마켓_톱렌즈', name: '마켓 톱렌즈 / 시장 분석', test: t => t.includes('마켓 톱렌즈') || t.includes('Market') || t.includes('Volatility of KOSDAQ') || t.includes('Panic') || t.includes('FOMC') },
  { id: 'Mathematics_of_Gambling', name: 'Mathematics of Gambling 시리즈', test: t => t.includes('Mathematics of Gambling') || t.includes('Gambling') },
  { id: '상한가_Momentum', name: '상한가 Momentum 시리즈', test: t => t.includes('상한가') || t.includes('상한가Momentum') },
  { id: 'Theorie_de_la_speculation', name: 'Theorie de la speculation 시리즈', test: t => t.includes('Theorie de la speculation') || t.includes('speculation') },
  { id: '김덕식_과학투자', name: '김덕식의 과학투자 시리즈', test: t => t.includes('김덕식') || t.includes('과학투자') },
  { id: 'General_Theory', name: 'General Theory 시리즈', test: t => t.includes('General Theory') || (t.includes('거래이론') && t.includes('분석')) },
  { id: 'data_regulation', name: '금융규제/세법/IB 자료 모음', test: t => t.includes('data_regulation') || t.includes('data_tax') || t.includes('data_ibanking') },
];

function generateSeriesInsight(id, matched) {
  const count = matched.length;
  const first = matched[0];
  const last = matched[count-1];
  
  switch(id) {
    case '켈리기준_자금관리':
      return `이 시리즈는 큐래프트 카페의 **핵심 정체성**을 이루는 가장 완성도 높은 콘텐츠입니다.

### 주요 흐름
1. **이론 도입 (2006)**: \`Mathematics of Gambling\`, \`Kelly Criterion Classic\`으로 도박/투자 수학의 기초 이론 수입
2. **전략 심화 (2007~2008)**: \`Growth Versus Security in Dynamic Investment Analysis\`, \`On the Role of the Growth Optimal Portfolio\`로 동적 투자 환경에서의 켈리 공식 확장
3. **FAQ 체계화 (2011)**: \`makilee\`가 \`켈리기준 #1~#8\`과 \`FAQ\`를 연재하며 이론을 체계적으로 정리
4. **실전 적용 (2011~2013)**: \`풀켈리 vs 하프켈리\`, \`가치투자와의 접목\`, \`Bill Ziemba 번역\`, \`NAV 기반 켈리비율\` 등 실전 문제 다룸

### 핵심 학습 가이드
- **입문**: \`켈리기준 FAQ 정리\` → \`과학적인 자금관리 전략\`
- **중급**: \`켈리기준 #1~#5\` (\`makilee\` 연재)
- **심화**: \`켈리 Fraction의 부정확성\`, \`동적 투자 분석(Growth vs Security)\`, \`CAPM과의 관계\``;
    
    case 'Statistical_Arbitrage':
      return `**2006년을 중심으로 한 퀀트 이론의 황금기**를 보여주는 시리즈입니다.

### 주요 흐름
- **기초 이론**: \`A Market Neutral Statistical Arbitrage Trading Model\`, \`Behavioral Statistical Arbitrage\`
- **페어 트레이딩**: \`Pairs Trading, Convergence Trading, Cointegration\`
- **머신러닝 적용**: \`Wavelets and Artificial Neural Networks\`, \`Random Matrix Approach\`, \`Computational Intelligence\`
- **파생상품**: \`Relative Implied Volatility Arbitrage\`, \`Gold and Silver Spread Trading\`
- **재무이론 융합**: \`Market Efficiency\`, \`Momentum and Value Strategies\`와의 연계

### 핵심 학습 가이드
- 통계적 차익거래의 수학적 정의와 전제조건 이해
- \`Pairs Trading\`과 \`Cointegration\`의 관계
- 머신러닝 기법(Wavelet, ANN)이 전통적 통계 모델과 어떻게 결합되는지 파악`;

    case 'Global_Momentum':
      return `**크래프트캐피탈**이 실제 운용하는 글로벌 모멘텀 전략의 **실전 성과 보고서** 모음입니다.

### 주요 흐름
- **2015년**: 4월, 6월, 7월, 8월~10월, 12월의 월별/분기별 성과 공유
- **2016년**: 포트폴리오 단위의 \`성과(리포트)\` 공유 시작
- 전략의 핵심은 **추세추종(Trend Following)**과 **글로벌 자산 배분**

### 핵심 학습 가이드
- 단순한 이론서가 아닌, **실제 운용 결과**를 통해 전략의 생명주기와 드로다운(drawdown)을 관찰
- 모멘텀 전략이 어떤 시장 환경에서 수익/손실이 나는지 시기별로 분석`;

    case 'Python_Finance':
      return `**Python을 금융 데이터 처리 및 트레이딩 시스템에 적용한 구현기**입니다.

### 주요 흐름
1. **환경 구축 (2012.02)**: \`Python Finance 패키지 설치\`, \`Pandas를 이용한 Tick→OHLC 변환\`
2. **ATS(자동매매시스템) 개발 (2012.04~2013.01)**: \`Tick_FU9Z v2.0~v2.2\`, \`공지사항을 이용한 Python Finance\` 연재
3. **고급 주제 (2012.08~)**: \`JP Morgan의 FPGA 전략\`, \`버려지는 매수매도 전략\`

### 핵심 학습 가이드
- \`Pandas\` 기반 금융 데이터 전처리
- 국내 파생상품(DDE 지원)과 Python 연동 구조
- HFT 및 FPGA와 Python의 상호보완 관계 이해`;

    case 'HFT':
      return `**고빈도 트레이딩(HFT)의 이론부터 하드웨어 가속까지** 다루는 시리즈입니다.

### 주요 흐름
- **이론/예측 (2011.08)**: \`Improving Accuracy of HFT forecasts\`, \`HFT 기초이론\`
- **코드/구현 (2011.08)**: \`분봉으로 바꿔주는 MATLAB 코드\`, \`변동성콘 with MATLAB\`
- **Market Making (2013.11~)**: \`Market Making by Dr. Sasha Stoikov\`
- **하드웨어 (2011.11~2012.08)**: \`CUDA with MATLAB\`, \`JP Morgan의 FPGA 전략\`
- **사회적 영향 (2012.08)**: \`고빈도매매가 금융시장에 미치는 질적 영향\`

### 핵심 학습 가이드
- HFT의 수익원은 **예측(forecasting)**과 **마켓메이킹(spread capture)**으로 양분됨
- 소프트웨어(MATLAB/Python) → GPU(CUDA) → FPGA로 이어지는 **지연시간(latency) 최적화** 단계 이해`;

    case 'Hidden_Markov_Model':
      return `**금융 시장의 체제 변환(regime switching)을 모델링하는 HMM** 관련 자료 모음입니다.

### 주요 흐름
- **기초 (2007.02)**: \`Markov Chain Monte Carlo Method Tutorial\`
- **고급 응용 (2008.02~2011.05)**: \`A Tutorial on Hidden Markov Models\`(Rabiner 원문), \`Hierarchical Hidden Markov Model of High-Frequency Market Regimes\`
- **실전 연결 (2008.02)**: \`륜에상스가 HMM을 선택해야 하는 이유\`

### 핵심 학습 가이드
- Rabiner의 \`A Tutorial on Hidden Markov Models\`은 음성인식 분야의 고전이지만, 금융 시장의 체제 변환 모델링에 직접 적용 가능
- HMM은 추세/횡보장 같은 **잠재 상태(latent state)**를 추론하는 데 탁월`;

    case 'Jim_Simons':
      return `**세계 최고의 퀀트 펀드, 륜에상스 테크놀로지와 그 창업자 Jim Simons**를 다루는 시리즈입니다.

### 주요 흐름
- **인물 소개 (2006.05~06)**: \`Jim Simons\`, \`the secret world of Jim Simons\`, \`Simons, Thorp and Shannon\`
- **인터뷰/기사 (2006.10~2008.02)**: 조선일보 인터뷰, \`Long Island's richest man\`, \`History of Renaissance Technologies\`
- **심화 분석 (2008.02)**: \`Letters from Simons to RIEF Investors\`
- **보유주식 리스트 (2007.10)**: \`Renaissance Technologies 보유주식 리스트\`

### 핵심 학습 가이드
- Simons이 수학자(다양체 기하학)에서 헤지펀드 운용자로 전환한 경로
- 륜에상스의 핵심 인재는 **물리학자, 수학자, 천문학자** 중심이라는 점
- Simons의 투자 철학과 데이터 중심 접근법의 역사적 의의`;

    case '마켓_톱렌즈':
      return `**주간/일간 단위의 시장 상황 분석 리포트** 성격의 글들입니다.

### 주요 흐름
- **2004년 말**: \`광기의장 개막\`, \`증시 위기 패턴 분석\`
- **2005년**: \`KOSDAQ Volatility\`, \`호재축적\` 등 개별 이벤트 분석
- **2006년 초**: \`Panic\`, \`시장 심리/매수 패격 분석\`
- **2007년**: \`FOMC\` 대응
- **2015년**: \`코스피의 적정고점과 상승장\`

### 핵심 학습 가이드
- 단순한 기술적 분석을 넘어, **시장 심리(공포/탐욕)**와 **거시 이벤트(FOMC, 유동성)**를 연결하는 관점 학습`;

    case 'Mathematics_of_Gambling':
      return `**도박의 수학**을 통해 켈리 공식과 기대效用 이론의 기초를 다루는 시리즈입니다.

### 주요 흐름
- 2006년 5월에 4편이 연속 업로드됨
- \`Mathematics of Gambling 1~4\`와 함께 \`Kelly criterion in blackjack, sports betting, and the stock market\`이 연계됨
- \`Casino\` 메뉴의 \`블랙잭 카드카운팅 기법\`과도 맞닿아 있음

### 핵심 학습 가이드
- 켈리 공식이 단순한 주식 투자 기법이 아니라, **도박/스포츠 베팅/금융 투자**를 관통하는 보편 원리임을 이해`;

    case '상한가_Momentum':
      return `**국내 주식 시장의 상한가 종목을 계량적으로 추적하는 전략** 개발기입니다.

### 주요 흐름
- **2012.11**: \`Intro\`와 \`기본 추출\`로 전략의 목적과 데이터 소스 정의
- **2012.11**: \`DB구축 및 기초조사\`로 데이터 인프라 설계
- 이 시리즈는 \`퀀트랩\`과 \`Python Finance\` 연재와 맞물려 있음

### 핵심 학습 가이드
- 국내 시장의 \`상한가\`라는 특수한 구조를 데이터 마이닝 관점에서 접근한 사례
- 전략 개발의 첫 단계는 **데이터 정의와 DB 설계**임을 확인`;

    case 'Theorie_de_la_speculation':
      return `**수리금융의 아버지 루이 바실리에(Louis Bachelier)**의 박사 논문 원문입니다.

### 주요 흐름
- 2006년 11월에 3편으로 분할 업로드됨
- \`Theorie de la speculation_1~3\`은 1900년 바실리에의 박사 논문 원문
- 2011년에는 \`루이 바실리에(Louis Bachelier)\`라는 소개글이 추가됨

### 핵심 학습 가이드
- 블랙-숄즈 이전, **브라운 용동을 주가 모델링에 최초로 적용**한 역사적 문서
- 현대 금융공학의 근원을 직접 접할 수 있는 기회`;

    case '김덕식_과학투자':
      return `**김덕식**이라는 필명(또는 필자)의 \`과학투자\` 칼럼/연재 모음입니다.

### 주요 흐름
- **2006년 말~2007년 초**: \`1.4조원을 받는 방법\`, \`통계적 차익거래 1~2\`, \`도박에서 배우는 투자기법\`, \`기술적 분석의 방향\`, \`공지사항 자동화\`, \`금융관리 전략\` 등
- \`quote_financial\` 메뉴에 링크 스크랩 형태로 집중 업로드됨

### 핵심 학습 가이드
- 국내 언론/블로그를 통해 소개된 **대중 과학 투자** 콘텐츠
- 학술 논문과 달리, 실전 투자자의 관점에서 이론을 풀어낸 글들`;

    case 'General_Theory':
      return `**큐래프트 카페의 창립기 지식 기둥**으로, 거래의 기초 이론을 다룹니다.

### 주요 흐름
- **2004년 6~8월**: \`거래이론 분석 이론의 기본\`, \`매수매도 모델의 몬테카를로\`, \`주가의 부분식\`, \`이동평균선의 분석과 응용\`
- **2004년 11~12월**: \`거래이론 분석 이론의 기초 1~2\`, \`Why Volume?\`
- **2005년 1월**: \`일반이론 #1\`
- **2007년 2월**: \`volatility trading strategy\`
- **2007년 7월**: \`거래이론 개요 VSA#1\`

### 핵심 학습 가이드
- 기술적 분석의 현대적 재해석
- 확률과 통계를 기반으로 한 매수/매도 결정 모델링의 초기 형태`;

    case 'data_regulation':
      return `**금융 규제, 세법, 투자은행(IB) 관련 법률/제도 자료** 모음입니다.

### 주요 흐름
- **2007년 1월**: \`증권시장 업무규정\`, \`상장회사 공시\`, \`CB/전환사채\` 등 국내 증권 규정 일람
- **2007년 4월**: \`조세회피지역\`, \`이중과세조정\`, \`법인세법\`, \`소득세법\`, \`offshore 서비스\`
- **2007년 4월**: \`Bermuda\`, \`Cayman Islands\`, \`US Virgin Islands\` 등 조세도피처 관련 IB 자료

### 핵심 학습 가이드
- 퀀트 트레이더도 **규제와 세법**을 이해해야 한다는 이 카페의 전제
- 국내외 금융 구조(특히 offshore 펀딩)의 법률적 토대 이해`;

    default:
      return `이 시리즈는 총 ${count}편으로, ${first.date}부터 ${last.date}까지 이어졌습니다. 날짜 순으로 목록을 따라 읽으며 주제의 흐름을 파악하는 것을 추천합니다.`;
  }
}

seriesDefs.forEach(({id, name, test}) => {
  const matched = posts.filter(p => test(p.title) || test(p.menu) || test(p.author)).sort((a,b) => a.date.localeCompare(b.date));
  if (matched.length === 0) return;
  
  const authors = {};
  matched.forEach(p => authors[p.author] = (authors[p.author] || 0) + 1);
  const authorList = Object.entries(authors).sort((a,b) => b[1] - a[1]).map(([k,v]) => `- ${k}: ${v}편`).join('\n');
  
  const tableRows = matched.map(p => `| ${p.date} | ${p.author} | ${p.menu} | ${p.title} |`).join('\n');
  
  const content = `# ${name}

> 총 ${matched.length}편의 글이 수집되었습니다.  
> 이 문서는 해당 시리즈의 전체 목록과 핵심 흐름을 정리한 학습 가이드입니다.

---

## 1. 개요

- **총 글 수**: ${matched.length}편
- **주요 기여자**:
${authorList}
- **시간 범위**: ${matched[0].date} ~ ${matched[matched.length-1].date}

---

## 2. 글 목록 (날짜 순)

| 날짜 | 작성자 | 메뉴 | 제목 |
|:---:|:---|:---|:---|
${tableRows}

---

## 3. 학습 포인트 및 흐름 분석

${generateSeriesInsight(id, matched)}

---

> **분석일**: 2026-04-16
`;

  fs.writeFileSync(path.join('큐래프트 스크래핑/시리즈별_정리', `${id}.md`), content, 'utf8');
  console.log('Created series:', id, '-', matched.length, 'posts');
});

// Yearly analysis
const yearPosts = {};
posts.forEach(p => {
  const yy = p.date.substring(0, 2);
  if (yy && !isNaN(yy)) {
    const fullYear = parseInt(yy) >= 50 ? `19${yy}` : `20${yy}`;
    if (!yearPosts[fullYear]) yearPosts[fullYear] = [];
    yearPosts[fullYear].push(p);
  }
});

function getYearFeature(year, count) {
  const features = {
    '2004': '카페 창립기. 다양한 실험적 주제(이론, 다크레코드, 카지노, 신비주의)가 폭발적으로 등장',
    '2005': '시스템 트레이딩 이론 심화. 거래이론과 모델디자이너 활성화',
    '2006': '퀀트 이론의 황금기. Statistical Arbitrage, Kelly Criterion, Simons, Behavior Finance 대량 유입',
    '2007': '커리어+규제 확장기. 구인 글 증가, HMM, Casino 이론, 금융규제/세법 다각화',
    '2008': '금융위기 직후. Renaissance Technologies 심화 분석과 이론 정리',
    '2009': '위기 후 침체기. 극소수 활동만',
    '2010': '극심한 침체기. 커뮤니티 활동 거의 중단',
    '2011': '실전 툴 전환기. MATLAB, Python Finance, HFT, CUDA, SVM, Kalman Filter 등 코드 중심 전환',
    '2012': '시스템 구축기. Python ATS, Tick 데이터, 상한가 Momentum, FPGA/HFT 구현',
    '2013': '정체기. 소수의 켈리공식/Python 연재만 지속',
    '2015': '글로벌 전략 성숙기. Global Momentum 성과 공유 체계화',
    '2016': '현대 퀀트 완성기. 프랙탈 지표, 장기투자 원칙, 횡보장 필터링',
    '2017': '소폭 활동 지속. 성과 공유 위주',
    '2018': '활동 둔화. 거의 휴지기',
    '2019': '활동 둔화. 소수 글만',
    '2024': 'AI/기술 융합기 시작. AI반도체 기술인재 대회',
    '2025': 'AI/기술 융합 지속. 최신 기술 행사 및 정보 공유'
  };
  return features[year] || '특별한 시대적 사건 없이 커뮤니티 활동 지속';
}

function getYearInsight(year) {
  const insights = {
    '2004': `2004년은 큐래프트 카페의 **원년**입니다.
- \`General Theory\`를 통해 거래의 수학적/통계적 기초를 세우려 했고,
- \`Dark Record\`, \`Casino\`, \`마법의성원\`, \`사이비종교\` 등 다양한 "지식의 경계"를 넘나드는 실험이 이루어졌습니다.
- \`괴달\`이라는 핵심 인물이 이 시기 대부분의 콘텐츠를 생산했습니다.
- **학습 포인트**: 초기 커뮤니티의 다양한 시도 중, \`General Theory\`와 \`모델디자이너\` 관련 글은 현재까지도 기초 이론으로서 가치가 있습니다.`,

    '2005': `2005년은 **이론의 심화**와 **시장 분석의 체계화**가 이루어진 해입니다.
- \`거래이론\` 시리즈가 지속되고, \`모델디자이너\`에서 본격적인 모델링 논의가 시작됩니다.
- \`마켓 톱렌즈\`가 등장하며 시장 리뷰 문화가 형성됩니다.
- **학습 포인트**: \`Stock Market Wizard 인터뷰\`, \`산가물치 옵션 가이드\` 등 실전서적 번역/소개가 활발했던 시기입니다.`,

    '2006': `2006년은 큐래프트 카페 역사상 **가장 중요한 이론 도입기**입니다.
- \`Mathematics of Gambling\`, \`Kelly Criterion\`, \`Statistical Arbitrage\` 등 서구 퀀트 핵심 이론이 대량 유입됩니다.
- \`Jim Simons\`와 \`Renaissance Technologies\`가 소개되며, **"세계 최고의 퀀트는 무엇을 하는가"**에 대한 롤모델이 제시됩니다.
- \`Behavioral Finance\`, \`Asset Pricing\`, \`Applied Quantitative Finance\` 등 학술 자료가 폭발적으로 증가합니다.
- **학습 포인트**: 이 해의 거의 모든 글이 "필수 학습 자료" 수준입니다. 특히 \`Statistical Arbitrage\` 시리즈와 \`Behavioral Statistical Arbitrage\`, \`Asset Pricing\`은 현대 퀀트의 기초를 이룹니다.`,

    '2007': `2007년은 **이론에서 실전/커리어로의 확장**이 이루어진 해입니다.
- \`구인\` 게시판이 활성화되며 국내외 증권사의 Quant Developer, Trader 채용 정보가 유통됩니다.
- \`data_regulation\`, \`data_tax\`, \`data_ibanking\` 메뉴가 생기며 **금융의 법률/제도적 인프라**도 학습 대상으로 포함됩니다.
- \`Log-Periodic Anti-Bubble\`, \`Order Flow\`, \`HMM\` 등 첨단 학술 주제가 지속적으로 유입됩니다.
- **학습 포인트**: \`Quant Hedge Fund Job Interview Questions\`는 커리어 준비의 고전이며, \`Evidence of a Worldwide Stock Market Log-Periodic Anti-Bubble\`은 복잡계 물리학을 금융에 접목한 흥미로운 사례입니다.`,

    '2008': `2008년은 **글로벌 금융위기 직후**의 반성과 정리가 이루어진 해입니다.
- \`Renaissance Technologies\` 관련 심화 분석이 이어지며, "위기 속에서도 수익을 낸 퀀트"의 비밀에 주목합니다.
- \`Matlab Terminal Speed\`, \`HMM Tutorial\` 등 기술적 기초도 함께 다집니다.
- **학습 포인트**: 위기 시기에 어떤 전략이 버티고, 어떤 전략이 물러섰는지를 분석하는 관점이 중요합니다.`,

    '2009': `2009년은 위기 후의 침체기로, 글 수가 극소수입니다.
- \`Why are information theorists so successful in the markets?\`와 같은 이론적 성찰만 남아있습니다.
- **학습 포인트**: 활동이 적은 시기이므로, 주변 연도(2008, 2011)와 함께 묶어 학습하는 것이 좋습니다.`,

    '2010': `2010년은 커뮤니티 활동의 최저점입니다.
- 1개의 글만 수집되었습니다.
- **학습 포인트**: 2006~2007년의 이론 도입과 2011년의 실전 전환 사이의 휴지기로 이해합니다.`,

    '2011': `2011년은 **이론에서 코드와 하드웨어로의 전환기**입니다.
- \`Python Finance\`, \`HFT 기반\`, \`알고리즘 트레이딩\`, \`CUDA with MATLAB\` 등 **구현 중심**의 콘텐츠가 폭발합니다.
- \`켈리기준\`도 \`FAQ\`와 \`#1~#8\` 시리즈로 체계적으로 정리됩니다.
- \`SVM\`, \`Kalman Filter\`, \`Machine Learning\` 등 머신러닝 기법이 시장 예측에 본격적으로 적용됩니다.
- **학습 포인트**: 이 해의 글들은 "어떻게 코딩하고, 어떻게 시스템을 구축하는가"에 대한 실전 매뉴얼입니다. 특히 \`CUDA\`, \`HFT\`, \`Python Finance\`는 구현 지향 학습자에게 필수입니다.`,

    '2012': `2012년은 **실제 트레이딩 시스템을 구축하는 구현의 해**입니다.
- \`Python ATS Tick_FU9Z v2.0~v2.2\`를 통해 Python 기반 자동매매시스템의 전체 구조가 공개됩니다.
- \`상한가 Momentum\` 시리즈가 데이터베이스 구축부터 시작합니다.
- \`HFT by Python\`에서 \`JP Morgan의 FPGA 전략\`까지, **소프트웨어→하드웨어**로 이어지는 최적화 논의가 이루어집니다.
- **학습 포인트**: \`Tick_FU9Z\` 시리즈는 국내 파생상품 시장에서 Python을 연동한 희귀한 실전 사례입니다.`,

    '2013': `2013년은 2012년의勢를 이어가지 못하고 정체기에 접어듭니다.
- 소수의 \`Python Finance\`, \`켈리기준\` 연재만 남아있습니다.
- **학습 포인트**: 이 해의 글들은 2011~2012년 시리즈의 마무리/보충 자료 성격이 강합니다.`,

    '2015': `2015년은 **글로벌 모멘텀 전략의 성숙**이 가시화된 해입니다.
- \`크래프트캐피탈\`이 \`Global Momentum\` 성과를 월별/분기별로 체계적으로 공유합니다.
- \`글로벌 멀티에셋 추세추종 포트폴리오\`, \`중국 선물 백테스팅\` 등 다양한 자산 클래스로 확장합니다.
- **학습 포인트**: 단순한 이론이 아닌, **실제 운용 결과**를 통해 전략의 생명주기를 관찰할 수 있습니다.`,

    '2016': `2016년은 **현대 퀀트의 완성**을 보여주는 해입니다.
- \`프랙탈 지표를 이용한 횡보장 필터링 전략\`: 추세와 횡보를 구분하는 첨단 기법
- \`장기 투자에서 성공하기 위한 핵심 원칙 2 (31)\`: 장기 투자의 심리학과 원칙
- **학습 포인트**: 단기 트레이딩과 장기 투자, 추세 추종과 횡보장 필터링이라는 상반된 개념을 모두 다루는 성숙한 논의입니다.`,

    '2017': `2017년은 소폭의 활동 지속기입니다.
- \`HFT\`와 \`Market Making\` 관련 고급 주제가 남아있습니다.
- **학습 포인트**: 2016년과 함께 묶어 현대 퀀트의 마무리 단계로 학습합니다.`,

    '2018': `2018년은 휴지기입니다.
- 1개의 글만 수집되었습니다.
- **학습 포인트**: 2015~2017년의 Global Momentum/HFT 논의가 정점을 찍은 후의 휴지기입니다.`,

    '2019': `2019년은 극소수 활동만 지속됩니다.
- **학습 포인트**: 2024년 AI 트렌드와의 연결고리를 찾기 어려운 시기입니다.`,

    '2024': `2024년은 **AI와 반도체를 중심으로 한 기술 융합**의 시작입니다.
- \`AI반도체\` 작성자가 \`AI반도체 기술인재(소프트웨어) 선발대회\`를 소개하며, 전통적인 퀀트 금융 커뮤니티가 최신 기술 트렌드로 확장됨을 보여줍니다.
- **학습 포인트**: 20년 전의 \`Python Finance\`, \`CUDA\`와 마찬가지로, **새로운 기술 패러다임이 금융과 만나는 접점**을 주목해야 합니다.`,

    '2025': `2025년은 AI/기술 융합이 지속되는 해입니다.
- \`2am 정진운과 함께하는 이태원 콘서트와 김포아라뱃길 칵테일 크루즈 파티\` 등 기술 행사/네트워킹 정보가 공유됩니다.
- **학습 포인트**: 커뮤니티가 단순한 온라인 지식 공유를 넘어, **오프라인 네트워크와 기술 행사**로 확장되고 있음을 확인합니다.`
  };
  return insights[year] || `**${year}년**은 특별한 시대적 사건 없이 커뮤니티 활동이 지속된 해입니다.\n- **학습 포인트**: 이 해의 글들은 전후 연도의 흐름과 함께 묶어 학습하는 것을 추천합니다.`;
}

Object.entries(yearPosts).sort((a,b) => a[0].localeCompare(b[0])).forEach(([year, list]) => {
  list.sort((a,b) => a.date.localeCompare(b.date));
  
  const menus = {};
  list.forEach(p => menus[p.menu] = (menus[p.menu] || 0) + 1);
  const menuList = Object.entries(menus).sort((a,b) => b[1] - a[1]).slice(0, 8).map(([k,v]) => `- ${k}: ${v}편`).join('\n');
  
  const authors = {};
  list.forEach(p => authors[p.author] = (authors[p.author] || 0) + 1);
  const authorList = Object.entries(authors).sort((a,b) => b[1] - a[1]).slice(0, 5).map(([k,v]) => `- ${k}: ${v}편`).join('\n');
  
  const notable = list.filter(p => 
    p.title.includes('Kelly') || p.title.includes('켈리') ||
    p.title.includes('Simons') || p.title.includes('Renaissance') ||
    p.title.includes('Statistical Arbitrage') || p.title.includes('Python') ||
    p.title.includes('HFT') || p.title.includes('Anti-Bubble') ||
    p.title.includes('Order Flow') || p.title.includes('Mathematics') ||
    p.title.includes('Global Momentum') || p.title.includes('CUDA') ||
    p.title.includes('FPGA') || p.title.includes('Kalman') ||
    p.title.includes('SVM') || p.title.includes('Bachelier') ||
    p.title.includes('HMM') || p.title.includes('Behavioral')
  ).map(p => `- [${p.date}] ${p.title} (${p.author})`).join('\n') || '(특별히 두드러진 단일 주제 없음)';
  
  const tableRows = list.map(p => `| ${p.date} | ${p.author} | ${p.menu} | ${p.title} |`).join('\n');
  
  const content = `# ${year}년 주제 흐름 분석

> 총 ${list.length}편의 글이 수집되었습니다.

---

## 1. 연도 개요

- **총 글 수**: ${list.length}편
- **활동 기간**: ${list[0].date} ~ ${list[list.length-1].date}
- **핵심 특징**: ${getYearFeature(year, list.length)}

---

## 2. 메뉴(게시판)별 분포 TOP 8

${menuList}

---

## 3. 주요 활동자 TOP 5

${authorList}

---

## 4. 주목할 만한 글들

${notable}

---

## 5. 시대적 맥락 및 학습 포인트

${getYearInsight(year)}

---

## 6. 전체 글 목록 (날짜 순)

| 날짜 | 작성자 | 메뉴 | 제목 |
|:---:|:---|:---|:---|
${tableRows}

---

> **분석일**: 2026-04-16
`;

  fs.writeFileSync(path.join('큐래프트 스크래핑/연도별_정리', `${year}.md`), content, 'utf8');
  console.log('Created year:', year, '-', list.length, 'posts');
});

console.log('All done!');
