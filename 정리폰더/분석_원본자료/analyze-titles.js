const fs = require('fs');
const path = require('path');

const base = '큐래프트 스크래핑/output-qraft';
let posts = [];

fs.readdirSync(base).filter(d => !d.endsWith('.json')).forEach(author => {
  const dir = path.join(base, author);
  fs.readdirSync(dir).filter(p => fs.statSync(path.join(dir, p)).isDirectory()).forEach(post => {
    try {
      const m = JSON.parse(fs.readFileSync(path.join(dir, post, 'meta.json'), 'utf8'));
      posts.push(m);
    } catch (e) {}
  });
});

// Sort by date
posts.sort((a, b) => a.date.localeCompare(b.date));

console.log(`총 수집된 글 수: ${posts.length}개\n`);

// Menu distribution
const menus = {};
posts.forEach(p => menus[p.menu] = (menus[p.menu] || 0) + 1);
console.log('=== 메뉴(게시판)별 분포 ===');
Object.entries(menus).sort((a, b) => b[1] - a[1]).forEach(([k, v]) => console.log(`${k}: ${v}개`));

// Year distribution
const years = {};
posts.forEach(p => {
  const yy = p.date.substring(0, 2);
  if (yy && !isNaN(yy)) {
    const fullYear = parseInt(yy) >= 50 ? `19${yy}` : `20${yy}`;
    years[fullYear] = (years[fullYear] || 0) + 1;
  }
});
console.log('\n=== 연도별 글 분포 ===');
Object.entries(years).sort((a, b) => a[0].localeCompare(b[0])).forEach(([k, v]) => console.log(`${k}년: ${v}개`));

// Keyword analysis
const keywords = {
  '켈리/Kelly/자금관리': ['켈리', 'Kelly', '자금관리', '배팅', 'betting'],
  '퀀트/Quant': ['퀀트', 'Quant', 'quant'],
  '통계적 차익거래/StatArb': ['통계적 차익거래', 'Statistical Arbitrage', 'statistical arbitrage', 'arbitrage', '차익거래'],
  'HFT/고빈도': ['HFT', '고빈도', 'high frequency'],
  '모멘텀/추세': ['모멘텀', 'momentum', '추세', 'trend'],
  '머신러닝/ML/AI': ['machine learning', 'neural network', 'neural', 'SVM', 'kalman', 'AI', '알고리즘'],
  '변동성/Volatility': ['변동성', 'volatility', 'vol'],
  '옵션/Option': ['옵션', 'option'],
  'Simons/륜에상스': ['Simons', 'simons', '륜에상스', 'Renaissance'],
  '파이썬/MATLAB': ['Python', 'python', 'MATLAB', 'matlab', '펄', 'Perl'],
  '모델/전략': ['모델', 'model', '전략', 'strategy', 'trading'],
  '데이터/분석': ['data', 'analysis', '데이터', '분석'],
  '구인/채용': ['구인', 'Quant Developer', 'Researcher', 'Developer', 'manager'],
  '금융공학/이론': ['금융공학', 'asset pricing', 'financial economics', 'behavioral', '공식'],
  '시장/거래': ['시장', 'market', '거래', 'trading', '주식', '증권']
};

const keywordCounts = {};
Object.keys(keywords).forEach(cat => keywordCounts[cat] = 0);

posts.forEach(p => {
  const text = `${p.title} ${p.menu}`;
  Object.entries(keywords).forEach(([cat, words]) => {
    if (words.some(w => text.includes(w))) {
      keywordCounts[cat]++;
    }
  });
});

console.log('\n=== 키워드 주제별 분포 (중복 허용) ===');
Object.entries(keywordCounts).sort((a, b) => b[1] - a[1]).forEach(([k, v]) => console.log(`${k}: ${v}개`));

// Series detection
const seriesPatterns = [
  { name: '켈리기준 자금관리 시리즈', test: t => t.includes('켈리') || t.includes('Kelly') },
  { name: 'HFT 관련 시리즈', test: t => t.includes('HFT') || t.includes('고빈도') },
  { name: 'Python Finance 시리즈', test: t => t.includes('Python Finance') || t.includes('Python') },
  { name: 'Global Momentum 성과 공유', test: t => t.includes('Global Momentum') || (t.includes('공유') && t.includes('성과')) },
  { name: '마켓 톱렌즈/시장 분석', test: t => t.includes('마켓 톱렌즈') || t.includes('Market') },
  { name: 'Mathematics of Gambling 시리즈', test: t => t.includes('Mathematics of Gambling') },
  { name: '김덕식의 과학투자 시리즈', test: t => t.includes('김덕식') || t.includes('과학투자') },
  { name: 'Jim Simons/륜에상스 시리즈', test: t => t.includes('Simons') || t.includes('simons') || t.includes('Renaissance') },
  { name: 'Statistical Arbitrage 시리즈', test: t => t.includes('Statistical Arbitrage') || t.includes('statistical arbitrage') },
  { name: 'Theorie de la speculation 시리즈', test: t => t.includes('Theorie de la speculation') },
  { name: '상한가 Momentum 시리즈', test: t => t.includes('상한가') || t.includes('상한가Momentum') },
  { name: 'Hidden Markov Model 시리즈', test: t => t.includes('HMM') || t.includes('Markov') },
];

console.log('\n=== 시리즈/연재물 분석 ===');
seriesPatterns.forEach(({name, test}) => {
  const count = posts.filter(p => test(p.title) || test(p.menu)).length;
  if (count > 0) console.log(`${name}: ${count}편`);
});

// Author activity
const authors = {};
posts.forEach(p => authors[p.author] = (authors[p.author] || 0) + 1);
console.log('\n=== 다산 저자 TOP 15 ===');
Object.entries(authors).sort((a, b) => b[1] - a[1]).slice(0, 15).forEach(([k, v]) => console.log(`${k}: ${v}편`));

// Notable standalone titles
console.log('\n=== 주목할 만한 단일 제목들 ===');
posts.filter(p => {
  const t = p.title;
  return t.includes('Log-Periodic') || t.includes('Anti-Bubble') ||
         t.includes('Caught on Tape') || t.includes('Order Flow') ||
         t.includes('Behavioral') || t.includes('Bachelier') ||
         t.includes('Interview') || t.includes('CUDA') || t.includes('FPGA');
}).forEach(p => console.log(`[${p.date}] ${p.title}`));

// Evolution timeline
console.log('\n=== 주제의 시대적 흐름 ===');
console.log('2004: 카페 창립기 - General Theory, 시스템 개발기, 블랙잭, 다크레코드');
console.log('2005~2006: 퀀트 이론 도입기 - Statistical Arbitrage, Kelly Criterion, Simons 소개');
console.log('2007: 구인/커리어, 규제/세법, HMM, Casino 이론 확장');
console.log('2008~2009: 금융위기 직후 - Renaissance, 륜에상스, 금융공학 이론 심화');
console.log('2010~2011: 실전 툴 전환 - MATLAB, Python Finance, HFT, 알고리즘 트레이딩');
console.log('2012: 시스템 구축 - Python ATS, Tick 데이터, 상한가 모멘텀');
console.log('2013~2015: 글로벌 전략 성숙기 - Global Momentum, 알고리즘 트레이딩 성과 공유');
console.log('2016: 현대 퀀트 완성기 - 프랙탈 지표, 장기투자 원칙, 횡보장 필터링');
console.log('2024~2025: AI/기술 융합 - AI반도체 대회, 최신 기술 행사');
