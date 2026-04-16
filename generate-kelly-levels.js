const fs = require('fs');
const path = require('path');

const base = '켈리기준_자금관리';
let posts = [];

fs.readdirSync(base).forEach(author => {
  const authorPath = path.join(base, author);
  if (!fs.statSync(authorPath).isDirectory()) return;
  fs.readdirSync(authorPath).forEach(folder => {
    const folderPath = path.join(authorPath, folder);
    if (!fs.statSync(folderPath).isDirectory()) return;
    const metaPath = path.join(folderPath, 'meta.json');
    if (!fs.existsSync(metaPath)) return;
    try {
      const meta = JSON.parse(fs.readFileSync(metaPath, 'utf8'));
      posts.push({ ...meta, author, folder, folderPath });
    } catch (e) {}
  });
});

posts.sort((a, b) => a.date.localeCompare(b.date));

// Classification logic
const advancedTitles = [
  'Kelly Criterion Classic',
  'Kelly criterion in blackjack, sports betting, and the stock market1',
  'Simons, Thorp and Shannon',
  'On the Role of the Growth Optimal Portfolio in Finance',
  'Growth Versus Security in Dynamic Investment Analysis',
  '[번외]켈리기준의 장단점 by Bill Ziemba',
  '최적포트폴리오 엔진 관련 논문 워킹페이퍼',
  '켈리 Fraction이 부정확 할 경우',
  '최근 N일의 데이터만으로 켈리비율을 구하는 베이지안 켈리자금관리의 성과',
  '켈리공식이라고 잘못 알려져있는 것',
  'Kelly 참고자료',
  '[문의] 켈리기준과 CAPM'
];

const advanced = posts.filter(p => advancedTitles.includes(p.title));
const intermediate = posts.filter(p => !advancedTitles.includes(p.title));

function generateMd(levelName, list, description, studyGuide) {
  const rows = list.map(p => `| ${p.date} | ${p.author} | ${p.title} | \`${p.author}/${p.folder}\` |`).join('\n');
  
  return `# 켈리기준 자금관리 - ${levelName}

> 켈리기준 자금관리 시리즈 39편 중 **${levelName}** 수준으로 분류된 ${list.length}편입니다.  
> ${description}

---

## 1. 개요

- **총 글 수**: ${list.length}편
- **시간 범위**: ${list[0].date} ~ ${list[list.length-1].date}
- **학습 난이도**: ${levelName === '중급' ? '🟡 중급 (Intermediate)' : '🔴 고급 (Advanced)'}

---

## 2. 글 목록 (날짜 순)

| 날짜 | 작성자 | 제목 | 원본 위치 |
|:---:|:---|:---|:---|
${rows}

---

## 3. 학습 포인트 및 추천 순서

${studyGuide}

---

> **분류 기준**: 제목과 메뉴(게시판) 키워드를 기반으로 난이도를 분류했습니다.  
> **분석일**: 2026-04-16
`;
}

const intermediateGuide = `### 3.1 중급 학습의 핵심 목표
이 단계에서는 **"켈리 공식이 무엇인지 안다"**는 전제 하에, **실제 투자에 어떻게 적용할 것인가**를 배웁니다.

### 3.2 추천 학습 순서

#### 단계 1: FAQ와 기초 체계화 (2011)
1. \`켈리기준 FAQ 정리\` (110709) — 전체 개념의 지도
2. \`켈리기준 #1\` ~ \`#8\` (110713~110803) — 단계별 개념 심화
   - #1: 기본 공식과 의미
   - #2~#4: 확률, 배당률, 손익비의 실측 문제
   - #5~#6: 여러 종목/포트폴리오에서의 적용
   - #7~#8: 변동성, 드로다운, 심리적 요인

#### 단계 2: 실전 적용과 비교 (2011)
3. \`풀켈리배팅과 하프켈리배팅의 비교\` (110713) — 가장 중요한 실전 선택지
4. \`켈리공식의 가치투자의 적용? 어떻게 할까요?\` (110729) — 가치투자와의 융합
5. \`어떤 전략을 선택할 것인가\` (111019) — 전략 선별 관점
6. \`How to measure your luck in System Trading\` (110927) — 자신의 엣지를 통계적으로 측정하는 법

#### 단계 3: Q&A와 사례 중심 반복 학습 (2006~2013)
- \`과학적인 자금관리 전략\` (여러 작성자) — 켈리 공식의 철학적 토대
- \`저기.. 질문이 있어 글을 올립니다.\` (drsquat, 트렌딩) — 초보자가 흔히 하는 질문과 답변의 맥락
- \`켈리 공식 계산 사이트가 맞나요?\` (110804) — 실제 계산 도구의 검증
- \`[문의] 전략의 선택 or 포트폴리오..\` (130302) — 포트폴리오 레벨에서의 적용
- \`켈리배팅에 관한 아이디어\` (130404) — 창의적 응용 사례

### 3.3 중급 학습자를 위한 팁
- **"풀켈리 vs 하프켈리"**는 반드시 이해해야 할 분기점입니다. 풀켈리는 이론적으로 최적이지만, 현실에서는 파산 위험이 있어 하프켈리(또는 그 이하)가 더 많이 쓰입니다.
- 켈리기준 #1~#8은 **순서대로** 읽는 것을 강력히 권장합니다. 괴달님이 쓴 이 연재물은 국내에서 켈리 공식을 가장 체계적으로 정리한 자료입니다.`;

const advancedGuide = `### 3.1 고급 학습의 핵심 목표
이 단계에서는 **켈리 공식을 단순한 공식 이상으로 확장**하여, 동적 투자 환경, 포트폴리오 이론, 베이지안 통계, 정보이론과의 연결을 탐구합니다.

### 3.2 추천 학습 순서

#### 단계 1: 고전 원문과 이론적 토대 (2006)
1. \`Kelly Criterion Classic\` (060510) — 켈리 원문의 핵심 아이디어
2. \`Kelly criterion in blackjack, sports betting, and the stock market1\` (060510) — **Edward Thorp**의 고전 논문. 도박→스포츠 베팅→주식 시장으로 이론을 확장한 역사적 문서
3. \`Simons, Thorp and Shannon\` (060525) — 정보이론의 아버지(Shannon), 퀀트의 아버지(Thorp), 륜에상스 창업자(Simons)의 연결고리

#### 단계 2: 성장최적포트폴리오와 동적 분석 (2006~2007)
4. \`On the Role of the Growth Optimal Portfolio in Finance\` (060831) — **Helmut Platen**의 학술 논문. 켈리 공식과 성장최적포트폴리오(GOP)가 금융 이론 전체에서 차지하는 위치
5. \`Growth Versus Security in Dynamic Investment Analysis\` (070416) — **동적 투자** 환경에서 성장(켈리)과 안정성(utility)의 트레이드오프를 수학적으로 분석

#### 단계 3: 현대적 확장과 정교한 응용 (2011~2012)
6. \`[번외]켈리기준의 장단점 by Bill Ziemba\` (110726) — 세계적 켈리 연구자의 요약
7. \`최적포트폴리오 엔진 관련 논문 워킹페이퍼\` (111019) — 포트폴리오 최적화 엔진과의 결합
8. \`켈리 Fraction이 부정확 할 경우\` (111118) — **부분 켈리(partial Kelly)**의 위험과 한계
9. \`최근 N일의 데이터만으로 켈리비율을 구하는 베이지안 켈리자금관리의 성과\` (111215) — **베이지안 통계**를 활용한 불확실성 하의 켈리 추정
10. \`켈리공식이라고 잘못 알려져있는 것\` (111227) — 대중적 오해와 개념적 정정
11. \`Kelly 참고자료\` (120417) — 추가 학술 자료
12. \`[문의] 켈리기준과 CAPM\` (120714) — **자본자산가격결정모형(CAPM)**과 켈리 공식의 관계

### 3.3 고급 학습자를 위한 팁
- **Thorp의 논문**은 현대 퀀트 트레이딩의 뿌리를 이해하는 데 필수입니다. "블랙잭 카드카운팅"에서 시작한 아이디어가 어떻게 주식 시장의 자금관리 전략이 되었는지를 보여줍니다.
- \`Growth Versus Security\`는 단순히 "켈리 공식을 써라"가 아니라, **유틸리티 함수(utility function)** 관점에서 얼마나 보수적/공격적으로 배팅해야 하는지를 수학적으로 다룹니다. 이를 이해하면 "하프켈리가 왜 더 나은가"에 대한 깊은 통찰을 얻게 됩니다.
- \`베이지안 켈리\`는 현실의 핵심 문제를 직접 다룹니다: "과거 데이터가 제한적일 때, 켈리 비율을 얼마나 신뢰할 수 있는가?"`;

fs.writeFileSync(path.join(base, '중급.md'), generateMd('중급', intermediate, '실제 투자에 적용하는 방법, FAQ 체계화, 풀/하프켈리 비교, 전략 선택, Q&A 중심.', intermediateGuide));
fs.writeFileSync(path.join(base, '고급.md'), generateMd('고급', advanced, '학술 논문 원문, 동적 투자 분석, 성장최적포트폴리오(GOP), 베이지안 켈리, CAPM과의 관계, 이론적 확장 중심.', advancedGuide));

console.log('Created 중급.md with', intermediate.length, 'posts');
console.log('Created 고급.md with', advanced.length, 'posts');
