const fs = require('fs');
const path = require('path');

const baseOutput = '큐래프트 스크래핑/output-qraft';
const seriesDir = '정리폰더/시리즈별_정리';

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

function copyRecursiveSync(src, dest) {
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    fs.mkdirSync(dest, { recursive: true });
    fs.readdirSync(src).forEach(child => {
      copyRecursiveSync(path.join(src, child), path.join(dest, child));
    });
  } else {
    fs.copyFileSync(src, dest);
  }
}

// Step 1: Build full post list with filesystem paths
console.log('Scanning original files...');
let allPosts = [];
fs.readdirSync(baseOutput).filter(d => !d.endsWith('.json')).forEach(author => {
  const authorPath = path.join(baseOutput, author);
  const stat = fs.statSync(authorPath);
  if (!stat.isDirectory()) return;
  
  fs.readdirSync(authorPath).forEach(postFolder => {
    const postPath = path.join(authorPath, postFolder);
    if (!fs.statSync(postPath).isDirectory()) return;
    
    const metaPath = path.join(postPath, 'meta.json');
    if (!fs.existsSync(metaPath)) return;
    
    try {
      const meta = JSON.parse(fs.readFileSync(metaPath, 'utf8'));
      allPosts.push({
        meta,
        author,
        postFolder,
        postPath
      });
    } catch (e) {}
  });
});
console.log('Found', allPosts.length, 'posts with meta.json');

// Step 2: For each series, create subfolder, move md (if needed), copy original files
seriesDefs.forEach(({ id, test }) => {
  const mdTopPath = path.join(seriesDir, `${id}.md`);
  const mdInnerPath = path.join(seriesDir, id, `${id}.md`);
  
  let targetDir;
  let mdExists = false;
  
  if (fs.existsSync(mdInnerPath)) {
    targetDir = path.join(seriesDir, id);
    mdExists = true;
    console.log('Resuming series:', id);
  } else if (fs.existsSync(mdTopPath)) {
    targetDir = path.join(seriesDir, id);
    fs.mkdirSync(targetDir, { recursive: true });
    fs.renameSync(mdTopPath, mdInnerPath);
    mdExists = true;
    console.log('Moved md ->', id);
  } else {
    console.log('Skipping (no md):', id);
    return;
  }
  
  const matched = allPosts.filter(p => test(p.meta.title) || test(p.meta.menu) || test(p.meta.author));
  if (matched.length === 0) {
    console.log('  No matching posts for', id);
    return;
  }
  
  console.log('  Copying', matched.length, 'posts for', id);
  
  matched.forEach(p => {
    const destDir = path.join(targetDir, p.author, p.postFolder);
    try {
      copyRecursiveSync(p.postPath, destDir);
    } catch (e) {
      console.error('    Copy failed:', p.postPath, '->', destDir, e.message);
    }
  });
});

console.log('Done organizing series folders!');
