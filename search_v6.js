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
  
  // Search for Xiaohongshu user profile URLs
  console.log("=== SEARCH: site:xiaohongshu.com 少儿图书 ===");
  await page.goto("https://www.baidu.com/s?wd=site%3Axiaohongshu.com+%E5%B0%91%E5%84%BF%E5%9B%BE%E4%B9%A6", {
    waitUntil: "domcontentloaded", timeout: 30000
  });
  await page.waitForTimeout(3000);
  
  const xhsLinks = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll(".result, .c-container").forEach(el => {
      const link = el.querySelector("a")?.href || "";
      const title = el.querySelector("h3, .t")?.textContent?.trim() || "";
      if (link.includes("xiaohongshu.com")) results.push({ title, link });
    });
    return results.slice(0, 10);
  });
  xhsLinks.forEach((r, i) => console.log(`${i+1}. ${r.title}\n   ${r.link}`));
  
  // Search for Douyin user profile URLs
  console.log("\n=== SEARCH: site:douyin.com 少儿图书 ===");
  await page.goto("https://www.baidu.com/s?wd=site%3Adouyin.com+%E5%B0%91%E5%84%BF%E5%9B%BE%E4%B9%A6", {
    waitUntil: "domcontentloaded", timeout: 30000
  });
  await page.waitForTimeout(3000);
  
  const dyLinks = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll(".result, .c-container").forEach(el => {
      const link = el.querySelector("a")?.href || "";
      const title = el.querySelector("h3, .t")?.textContent?.trim() || "";
      if (link.includes("douyin.com")) results.push({ title, link });
    });
    return results.slice(0, 10);
  });
  dyLinks.forEach((r, i) => console.log(`${i+1}. ${r.title}\n   ${r.link}`));
  
  // Search for Xiaohongshu user: 图书推荐
  console.log("\n=== SEARCH: site:xiaohongshu.com 图书推荐 ===");
  await page.goto("https://www.baidu.com/s?wd=site%3Axiaohongshu.com+%E5%9B%BE%E4%B9%A6%E6%8E%A8%E8%8D%90", {
    waitUntil: "domcontentloaded", timeout: 30000
  });
  await page.waitForTimeout(3000);
  
  const xhsBookLinks = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll(".result, .c-container").forEach(el => {
      const link = el.querySelector("a")?.href || "";
      const title = el.querySelector("h3, .t")?.textContent?.trim() || "";
      if (link.includes("xiaohongshu.com")) results.push({ title, link });
    });
    return results.slice(0, 10);
  });
  xhsBookLinks.forEach((r, i) => console.log(`${i+1}. ${r.title}\n   ${r.link}`));
  
  // Search for 抖音 童书
  console.log("\n=== SEARCH: site:douyin.com 童书 ===");
  await page.goto("https://www.baidu.com/s?wd=site%3Adouyin.com+%E7%AB%A5%E4%B9%A6", {
    waitUntil: "domcontentloaded", timeout: 30000
  });
  await page.waitForTimeout(3000);
  
  const dyKidsLinks = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll(".result, .c-container").forEach(el => {
      const link = el.querySelector("a")?.href || "";
      const title = el.querySelector("h3, .t")?.textContent?.trim() || "";
      if (link.includes("douyin.com")) results.push({ title, link });
    });
    return results.slice(0, 10);
  });
  dyKidsLinks.forEach((r, i) => console.log(`${i+1}. ${r.title}\n   ${r.link}`));
  
  await ctx.close();
  await browser.close();
  console.log("\nDone!");
})();
