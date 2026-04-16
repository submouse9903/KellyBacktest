#!/usr/bin/env npx tsx
/**
 * 네이버 카페 특정 작성자 글 스크래핑 스크립트 (API + Puppeteer)
 *
 * 사용 예시:
 *   npx tsx scrape-cafe.ts --author-nickname "닉네임" --limit 10
 *   npx tsx scrape-cafe.ts --author-id <MEMBER_KEY> --limit 10
 *   npx tsx scrape-cafe.ts --all-authors --limit 50
 */

import puppeteer, { Page, Browser } from "puppeteer-extra";
import StealthPlugin from "puppeteer-extra-plugin-stealth";
import * as path from "path";
import * as fs from "fs";

puppeteer.use(StealthPlugin());

const CLUB_ID = 10591177;
const CAFE_BASE = "https://cafe.naver.com/volanalysis";
const LOGIN_URL = "https://nid.naver.com/nidlogin.login";
const COOKIES_FILE = "./naver-cookies.json";
const VIEWPORT = { width: 1440, height: 900 };

// Edge 실행 파일 경로 (Windows)
const EDGE_PATHS = [
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
];

function getEdgeExecutable(): string | undefined {
  for (const p of EDGE_PATHS) if (fs.existsSync(p)) return p;
  return undefined;
}

function loadCookies(): object[] | null {
  if (fs.existsSync(COOKIES_FILE)) {
    try { return JSON.parse(fs.readFileSync(COOKIES_FILE, "utf-8")); } catch { return null; }
  }
  return null;
}

function saveCookies(cookies: object[]): void {
  fs.writeFileSync(COOKIES_FILE, JSON.stringify(cookies, null, 2), "utf-8");
  console.log(`[Auth] 쿠키 저장 완료: ${COOKIES_FILE}`);
}

// ─── 대화형 로그인 ───────────────────────────────────────────────────────────

async function doInteractiveLogin(browser: Browser): Promise<boolean> {
  console.log("\n[Auth] 브라우저를 열어 로그인 페이지로 이동합니다.");
  console.log("[Auth] 네이버에 로그인한 후 브라우저를 그대로 두세요.\n");
  const page = await browser.newPage();
  await page.setViewport(VIEWPORT);
  await page.goto(LOGIN_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
  const maxWaitMs = 3 * 60 * 1000;
  const pollInterval = 2000;
  const startTime = Date.now();
  while (Date.now() - startTime < maxWaitMs) {
    await new Promise((r) => setTimeout(r, pollInterval));
    const currentUrl = page.url();
    if (!currentUrl.includes("nidlogin") && !currentUrl.includes("login")) {
      const cookies = await page.cookies();
      const naverCookies = cookies.filter((c) => c.domain.includes("naver.com"));
      saveCookies(naverCookies as object[]);
      await page.close();
      console.log("[Auth] 로그인 성공!\n");
      return true;
    }
  }
  await page.close();
  console.error("[Auth] 로그인 시간 초과");
  return false;
}

// ─── 글 목록 API 수집 ────────────────────────────────────────────────────────

type PostMeta = {
  articleId: number;
  url: string;
  title: string;
  dateTs: number;
  authorNickname: string;
  authorMemberKey: string;
  menuName: string;
};

async function fetchAllPosts(): Promise<PostMeta[]> {
  const posts: PostMeta[] = [];
  let pageNum = 1;
  while (true) {
    const url = `https://apis.naver.com/cafe-web/cafe-boardlist-api/v1/cafes/${CLUB_ID}/menus/0/articles?page=${pageNum}&pageSize=50&sortBy=TIME&viewType=L`;
    console.log(`[API] page ${pageNum}`);
    const res = await fetch(url, { headers: { "User-Agent": "Mozilla/5.0" } });
    if (!res.ok) {
      console.error(`[API] HTTP ${res.status}`);
      break;
    }
    const json = await res.json();
    const list = json?.result?.articleList || [];
    if (!Array.isArray(list) || list.length === 0) break;

    for (const row of list) {
      const item = row.item;
      if (!item) continue;
      posts.push({
        articleId: item.articleId,
        url: `${CAFE_BASE}/${item.articleId}`,
        title: item.subject || "",
        dateTs: item.writeDateTimestamp || 0,
        authorNickname: item.writerInfo?.nickName || "unknown",
        authorMemberKey: item.writerInfo?.memberKey || "",
        menuName: item.menuName || "",
      });
    }
    console.log(`  +${list.length}개 (총 ${posts.length}개)`);
    if (list.length < 50) break;
    pageNum++;
  }
  return posts;
}

// ─── 본문 추출 ───────────────────────────────────────────────────────────────

const CONTENT_SELECTORS = [
  ".se-main-container",      // Smart Editor 본문
  ".post_cont",              // 구형/일반 에디터 본문 (모바일)
  ".ArticleContentWrap",
  ".WebArticle",
  ".article_viewer",
  "#tbody",
  ".tbody",
  ".article",
  "[class*='article_content']",
];
const TITLE_SELECTORS = [".se-title-text", ".title_text", ".article_title", "h1"];
const DATE_SELECTORS = [".se_publishDate", ".date", ".article_info .date", "time"];
const COMMENT_SELECTORS = [
  ".CommonComment",
  ".talk_comment_wrap",
  ".ArticleComment",
  ".comment_list",
  ".comment_area",
  "#commentList",
  ".cafe_comment_list",
];

async function extractPostContent(browser: Browser, articleId: number): Promise<{
  title: string;
  date: string;
  contentHtml: string;
  contentText: string;
  commentsHtml: string;
  commentsText: string;
}> {
  const page = await browser.newPage();
  const savedCookies = loadCookies();

  // 쿠키 설정 (모바일 웹 접근 위해 HTTPS 프리네비게이션)
  if (savedCookies && savedCookies.length > 0) {
    await page.goto("https://cafe.naver.com/volanalysis", { waitUntil: "domcontentloaded", timeout: 20000 });
    await page.setCookie(...(savedCookies as Parameters<Page["setCookie"]>[0][]));
  }

  // 모바일 웹으로 본문 추출
  await page.setUserAgent(
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
  );
  await page.setViewport({ width: 375, height: 812, isMobile: true, hasTouch: true });

  await page.goto(`https://m.cafe.naver.com/ca-fe/web/cafes/${CLUB_ID}/articles/${articleId}`, {
    waitUntil: "networkidle2",
    timeout: 30000,
  });
  await new Promise((r) => setTimeout(r, 3000));

  const currentUrl = page.url();
  if (currentUrl.includes("nidlogin") || currentUrl.includes("login")) {
    throw new Error("쿠키가 만료되었습니다. --relogin 옵션으로 다시 로그인해주세요.");
  }

  const result = await page.evaluate(
    (contentSels: string[], dateSels: string[], titleSels: string[]) => {
      let title = "";
      for (const sel of titleSels) {
        const el = document.querySelector(sel);
        if (el?.textContent?.trim()) { title = el.textContent.trim(); break; }
      }
      if (!title) {
        const og = document.querySelector<HTMLMetaElement>('meta[property="og:title"]');
        title = og?.content?.trim() || "";
      }

      let date = "";
      for (const sel of dateSels) {
        const el = document.querySelector(sel);
        if (!el) continue;
        const dt = el.getAttribute("datetime") || el.textContent?.trim() || "";
        if (dt) { date = dt; break; }
      }

      let contentHtml = "";
      let contentText = "";
      for (const sel of contentSels) {
        const el = document.querySelector(sel);
        if (!el) continue;
        el.querySelectorAll("img").forEach((img) => {
          const realSrc =
            img.dataset.lazySrc ||
            img.dataset.src ||
            img.dataset.originalSrc ||
            img.getAttribute("data-lazy-src") ||
            img.getAttribute("data-src") ||
            img.src;
          if (realSrc && !realSrc.startsWith("data:")) img.src = realSrc;
          img.removeAttribute("width");
          img.removeAttribute("height");
          img.style.cssText = "max-width:100%!important;width:100%!important;height:auto!important;display:block;";
        });
        contentHtml = el.innerHTML;
        contentText = el.textContent?.trim() ?? "";
        break;
      }

      let commentsHtml = "";
      let commentsText = "";
      for (const sel of [
        ".CommonComment",
        ".talk_comment_wrap",
        ".ArticleComment",
        ".comment_list",
        ".comment_area",
        "#commentList",
        ".cafe_comment_list",
      ]) {
        const el = document.querySelector(sel);
        if (!el) continue;
        el.querySelectorAll("img").forEach((img) => img.remove());
        commentsHtml = el.innerHTML;
        commentsText = el.textContent?.trim() ?? "";
        break;
      }

      return { title, date, contentHtml, contentText, commentsHtml, commentsText };
    },
    CONTENT_SELECTORS,
    DATE_SELECTORS,
    TITLE_SELECTORS
  );

  await page.close();
  return result;
}

// ─── 유틸리티 ────────────────────────────────────────────────────────────────

function normalizeDate(ts: number, raw?: string): string {
  if (raw) {
    const m = raw.match(/(\d{4})[.\-\/T](\d{1,2})[.\-\/](\d{1,2})/);
    if (m) {
      const yy = m[1].slice(2);
      return `${yy}${m[2].padStart(2, "0")}${m[3].padStart(2, "0")}`;
    }
  }
  if (ts) {
    const d = new Date(ts);
    const yy = String(d.getFullYear()).slice(2);
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    return `${yy}${mm}${dd}`;
  }
  const now = new Date();
  const yy = String(now.getFullYear()).slice(2);
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  return `${yy}${mm}${dd}`;
}

function safeFileName(str: string, maxLen = 60): string {
  return str
    .replace(/[\\/:*?"<>|]/g, "")
    .replace(/\s+/g, "_")
    .replace(/[._]+$/g, "")
    .slice(0, maxLen)
    .replace(/[._]+$/g, "");
}

function scanCompletedUrls(authorDir: string): Set<string> {
  const completed = new Set<string>();
  if (!fs.existsSync(authorDir)) return completed;
  for (const entry of fs.readdirSync(authorDir, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const metaPath = path.join(authorDir, entry.name, "meta.json");
    if (!fs.existsSync(metaPath)) continue;
    try {
      const meta = JSON.parse(fs.readFileSync(metaPath, "utf-8"));
      if (meta.url) completed.add(meta.url);
    } catch {}
  }
  return completed;
}

// ─── 메인 ────────────────────────────────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2);
  const get = (flag: string) => {
    const i = args.indexOf(flag);
    return i !== -1 ? args[i + 1] : undefined;
  };

  const authorIdArg = get("--author-id");
  const authorNicknameArg = get("--author-nickname");
  const allAuthors = args.includes("--all-authors");
  const outputArg = get("--output-dir");
  const limitArg = get("--limit");
  const forceRelogin = args.includes("--relogin");

  if (!authorIdArg && !authorNicknameArg && !allAuthors) {
    console.error("Usage: npx tsx scrape-cafe.ts --author-id <ID> | --author-nickname <NAME> | --all-authors [--limit N] [--output-dir DIR]");
    process.exit(1);
  }

  const outputBaseDir = outputArg ?? "./output-qraft";
  const limit = limitArg ? parseInt(limitArg) : Infinity;
  fs.mkdirSync(outputBaseDir, { recursive: true });
  console.log(`\n[출력] ${outputBaseDir}\n`);

  // 인증
  const savedCookies = !forceRelogin ? loadCookies() : null;
  const needVisibleBrowser = !savedCookies || savedCookies.length === 0;

  const executablePath = getEdgeExecutable();
  console.log(`[Browser] ${executablePath ? `Microsoft Edge: ${executablePath}` : "Puppeteer 기본 Chromium"}`);

  const loginBrowser = await puppeteer.launch({
    headless: needVisibleBrowser ? false : true,
    executablePath,
    args: ["--no-sandbox", `--window-size=${VIEWPORT.width},${VIEWPORT.height}`],
    defaultViewport: VIEWPORT,
  });

  try {
    if (!needVisibleBrowser) {
      // 쿠키 유효성 검증 (Chromium으로 확인, Edge는 Family Safety 우회)
      const checkBrowser = await puppeteer.launch({ headless: true, args: ["--no-sandbox"] });
      const checkPage = await checkBrowser.newPage();
      await checkPage.goto("https://cafe.naver.com/volanalysis", { waitUntil: "domcontentloaded", timeout: 20000 });
      await checkPage.setCookie(...(savedCookies as Parameters<Page["setCookie"]>[0][]));
      await checkPage.setUserAgent(
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
      );
      await checkPage.setViewport({ width: 375, height: 812, isMobile: true, hasTouch: true });
      try {
        await checkPage.goto("https://m.cafe.naver.com/volanalysis/2251", { waitUntil: "domcontentloaded", timeout: 30000 });
      } catch {}
      await new Promise((r) => setTimeout(r, 2000));
      const ok = !checkPage.url().includes("nidlogin");
      await checkBrowser.close();
      if (ok) {
        console.log("[Auth] 저장된 쿠키로 카페 접근 확인됨.");
      } else {
        console.log("[Auth] 저장된 쿠키가 만료됨. 재로그인이 필요합니다.");
        const loginOk = await doInteractiveLogin(loginBrowser);
        if (!loginOk) { console.error("로그인 실패."); process.exit(1); }
      }
    } else {
      const loginOk = await doInteractiveLogin(loginBrowser);
      if (!loginOk) { console.error("로그인 실패."); process.exit(1); }
    }
  } finally {
    await loginBrowser.close();
  }

  // 본문 수집용 Chromium 브라우저
  const workBrowser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", `--window-size=${VIEWPORT.width},${VIEWPORT.height}`],
    defaultViewport: VIEWPORT,
  });

  try {
    console.log("=== Step 1: 전체 글 목록 API 수집 ===");
    const allPosts = await fetchAllPosts();
    if (allPosts.length === 0) { console.error("게시글을 찾을 수 없습니다."); process.exit(1); }

    let targetPosts = allPosts;
    if (authorIdArg) {
      targetPosts = allPosts.filter((p) => p.authorMemberKey === authorIdArg);
    } else if (authorNicknameArg) {
      targetPosts = allPosts.filter((p) => p.authorNickname.includes(authorNicknameArg));
    }

    if (targetPosts.length === 0) { console.error("조건에 맞는 작성자의 글이 없습니다."); process.exit(1); }

    if (limit < targetPosts.length) {
      console.log(`\n${limit}개로 제한 (대상 ${targetPosts.length}개 / 전체 ${allPosts.length}개)`);
      targetPosts = targetPosts.slice(0, limit);
    } else {
      console.log(`\n대상 ${targetPosts.length}개 (전체 ${allPosts.length}개)`);
    }

    const byAuthor: Record<string, PostMeta[]> = {};
    for (const p of targetPosts) {
      const nick = safeFileName(p.authorNickname, 30) || "unknown";
      if (!byAuthor[nick]) byAuthor[nick] = [];
      byAuthor[nick].push(p);
    }

    fs.writeFileSync(path.join(outputBaseDir, "post-urls.json"), JSON.stringify(targetPosts, null, 2));

    console.log("=== Step 2: 본문 추출 (작성자별 저장) ===");
    const results: any[] = [];

    for (const [authorNick, posts] of Object.entries(byAuthor)) {
      const authorDir = path.join(outputBaseDir, authorNick);
      fs.mkdirSync(authorDir, { recursive: true });
      const completed = scanCompletedUrls(authorDir);
      const pending = posts.filter((p) => !completed.has(p.url));
      if (pending.length === 0) { console.log(`[${authorNick}] 이미 모두 완료됨`); continue; }

      console.log(`\n[작성자: ${authorNick}] ${pending.length}개 처리`);

      for (let i = 0; i < pending.length; i++) {
        const { url, articleId, title: apiTitle, dateTs, authorNickname, menuName } = pending[i];
        console.log(`  [${i + 1}/${pending.length}] ${url}`);

        try {
          const { title, date, contentHtml, contentText, commentsHtml, commentsText } = await extractPostContent(workBrowser, articleId);

          // 모바일 페이지에서 제목 셀렉터가 실제 글 제목이 아닌 "전체글" 등을 반환할 수 있음
          let finalTitle = title;
          if (!finalTitle || finalTitle.includes("전체글") || finalTitle.includes("공식카페") || finalTitle.includes("카페홈") || finalTitle.length < 5) {
            finalTitle = apiTitle;
          }
          if (!finalTitle) finalTitle = `post-${articleId}`;
          const dateStr = normalizeDate(dateTs, date);
          const safeTitle = safeFileName(finalTitle);
          const folderName = `${dateStr}_${safeTitle}`;
          const postDir = path.join(authorDir, folderName);
          fs.mkdirSync(postDir, { recursive: true });

          const fullHtml = `<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${finalTitle}</title>
  <style>
    body { font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.8; }
    img { max-width: 100% !important; width: 100% !important; height: auto !important; display: block; margin: 8px 0; }
  </style>
</head>
<body>
  <h1>${finalTitle}</h1>
  <p style="color:#888; font-size:0.9em;">작성자: ${authorNickname} | 메뉴: ${menuName} | ${dateStr} · <a href="${url}">${url}</a></p>
  <hr>
  ${contentHtml}
</body>
</html>`;

          fs.writeFileSync(path.join(postDir, "content.html"), fullHtml, "utf-8");
          fs.writeFileSync(path.join(postDir, "content.txt"), contentText, "utf-8");
          fs.writeFileSync(path.join(postDir, "meta.json"), JSON.stringify({ title: finalTitle, author: authorNickname, menu: menuName, date: dateStr, url }, null, 2));

          if (commentsHtml || commentsText) {
            const commentsFullHtml = `<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>댓글 - ${finalTitle}</title>
  <style>
    body { font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; color: #333; }
    img { max-width: 100% !important; width: 100% !important; height: auto !important; display: block; margin: 8px 0; }
  </style>
</head>
<body>
  <h2>댓글</h2>
  <p style="color:#888; font-size:0.9em;">원문: <a href="${url}">${url}</a></p>
  <hr>
  ${commentsHtml}
</body>
</html>`;
            fs.writeFileSync(path.join(postDir, "comments.html"), commentsFullHtml, "utf-8");
            fs.writeFileSync(path.join(postDir, "comments.txt"), commentsText, "utf-8");
          }

          console.log(`    ✓ ${folderName}`);
          results.push({ url, success: true, author: authorNickname, title: finalTitle });
        } catch (e) {
          const error = e instanceof Error ? e.message : String(e);
          console.log(`    ✗ Error: ${error}`);
          results.push({ url, success: false, author: authorNickname, error });
        }

        if (i < pending.length - 1) await new Promise((r) => setTimeout(r, 1500));
      }
    }

    const succeeded = results.filter((r) => r.success).length;
    fs.writeFileSync(
      path.join(outputBaseDir, "summary.json"),
      JSON.stringify({ cafe: "volanalysis", total: targetPosts.length, succeeded, failed: targetPosts.length - succeeded }, null, 2)
    );

    console.log(`\n${"=".repeat(50)}`);
    console.log(`완료! ${succeeded}/${targetPosts.length}개 수집`);
    console.log(`출력: ${path.resolve(outputBaseDir)}`);
  } finally {
    await workBrowser.close();
  }
}

main().catch(console.error);
