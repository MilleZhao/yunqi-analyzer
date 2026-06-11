const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({
    headless: false,
    args: ["--disable-blink-features=AutomationControlled"]
  });
  
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    locale: "zh-CN"
  });
  
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => false });
    window.chrome = { runtime: {} };
  });
  
  const page = await ctx.newPage();
  
  // Search Xiaohongshu specific accounts
  console.log("=== SEARCH: 小红书 绘本 账号 推荐 名字 ===");
  await page.goto("https://www.baidu.com/s?wd=小红书+绘本+账号+推荐+名字", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(3000);
  
  const xhsAccounts = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll(".result, .c-container").forEach(el => {
      const title = el.querySelector("h3, .t")?.textContent?.trim() || "";
      const desc = el.querySelector(".c-abstract, .c-span-last, .c-row")?.textContent?.trim()?.substring(0, 300) || "";
      results.push({ title, desc });
    });
    return results.slice(0, 10);
  });
  xhsAccounts.forEach((r, i) => console.log(`${i+1}. ${r.title}\n   ${r.desc}`));
  
  // Open 青葫芦 百度百科 to find their Douyin ID
  console.log("\n=== Opening 青葫芦 Baidu Baike ===");
  await page.goto("https://www.baidu.com/s?wd=青葫芦官方旗舰店+抖音", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(2000);
  
  const qhl = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll(".result, .c-container").forEach(el => {
      const title = el.querySelector("h3, .t")?.textContent?.trim() || "";
      const desc = el.querySelector(".c-abstract, .c-span-last, .c-row")?.textContent?.trim()?.substring(0, 300) || "";
      results.push({ title, desc });
    });
    return results.slice(0, 5);
  });
  qhl.forEach((r, i) => console.log(`${i+1}. ${r.title}\n   ${r.desc}`));
  
  // Search: 小红书 读书博主 账号名
  console.log("\n=== SEARCH: 小红书 读书博主 账号名 2025 ===");
  await page.goto("https://www.baidu.com/s?wd=小红书+读书博主+账号名+2025", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(2000);
  
  const xhs2 = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll(".result, .c-container").forEach(el => {
      const title = el.querySelector("h3, .t")?.textContent?.trim() || "";
      const desc = el.querySelector(".c-abstract, .c-span-last, .c-row")?.textContent?.trim()?.substring(0, 300) || "";
      if (title || desc) results.push({ title, desc });
    });
    return results.slice(0, 10);
  });
  xhs2.forEach((r, i) => console.log(`${i+1}. ${r.title}\n   ${r.desc}`));
  
  // Search: 抖音 青葫芦 账号ID
  console.log("\n=== SEARCH: 抖音 青葫芦 用户ID ===");
  await page.goto("https://www.baidu.com/s?wd=douyin.com+青葫芦", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(2000);
  
  const qhlLinks = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll(".result, .c-container").forEach(el => {
      const link = el.querySelector("a")?.href || "";
      const title = el.querySelector("h3, .t")?.textContent?.trim() || "";
      if (link) results.push({ title, link });
    });
    return results.slice(0, 8);
  });
  qhlLinks.forEach((r, i) => console.log(`${i+1}. ${r.title}\n   ${r.link}`));
  
  // Try to open Xiaohongshu web explore page
  console.log("\n=== Trying Xiaohongshu Explore ===");
  await page.goto("https://www.xiaohongshu.com/explore", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(5000);
  
  const xhsPageData = await page.evaluate(() => {
    const title = document.title;
    const body = document.body?.innerText?.substring(0, 500) || "";
    return { title, body };
  });
  console.log("XHS Title:", xhsPageData.title);
  console.log("XHS Body:", xhsPageData.body);
  
  await page.screenshot({ path: "xhs_explore.png" });
  
  await ctx.close();
  await browser.close();
  console.log("\nDone!");
})();
