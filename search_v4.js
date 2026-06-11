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
  
  // Search 1: 抖音 图书推荐 博主
  console.log("=== SEARCH: 抖音 图书推荐 博主 ===");
  await page.goto("https://www.baidu.com/s?wd=抖音+图书推荐+博主+账号", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(3000);
  
  const r1 = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll(".result, .c-container").forEach(el => {
      const title = el.querySelector("h3, .t")?.textContent?.trim() || "";
      const desc = el.querySelector(".c-abstract, .c-span-last, .c-row")?.textContent?.trim()?.substring(0, 200) || "";
      results.push({ title, desc });
    });
    return results.slice(0, 10);
  });
  r1.forEach((r, i) => console.log(`${i+1}. ${r.title}\n   ${r.desc}`));
  
  // Search 2: 小红书 图书 博主 推荐
  console.log("\n=== SEARCH: 小红书 图书推荐 博主 ===");
  await page.goto("https://www.baidu.com/s?wd=小红书+图书推荐+博主+账号", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(3000);
  
  const r2 = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll(".result, .c-container").forEach(el => {
      const title = el.querySelector("h3, .t")?.textContent?.trim() || "";
      const desc = el.querySelector(".c-abstract, .c-span-last, .c-row")?.textContent?.trim()?.substring(0, 200) || "";
      results.push({ title, desc });
    });
    return results.slice(0, 10);
  });
  r2.forEach((r, i) => console.log(`${i+1}. ${r.title}\n   ${r.desc}`));
  
  // Search 3: 抖音 童书 绘本 账号
  console.log("\n=== SEARCH: 抖音 童书 绘本 账号 ===");
  await page.goto("https://www.baidu.com/s?wd=抖音+童书+绘本+账号+推荐", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(3000);
  
  const r3 = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll(".result, .c-container").forEach(el => {
      const title = el.querySelector("h3, .t")?.textContent?.trim() || "";
      const desc = el.querySelector(".c-abstract, .c-span-last, .c-row")?.textContent?.trim()?.substring(0, 200) || "";
      results.push({ title, desc });
    });
    return results.slice(0, 10);
  });
  r3.forEach((r, i) => console.log(`${i+1}. ${r.title}\n   ${r.desc}`));
  
  // Search 4: 小红书 童书 绘本 博主
  console.log("\n=== SEARCH: 小红书 童书 绘本 博主 ===");
  await page.goto("https://www.baidu.com/s?wd=小红书+童书+绘本+博主+推荐", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(3000);
  
  const r4 = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll(".result, .c-container").forEach(el => {
      const title = el.querySelector("h3, .t")?.textContent?.trim() || "";
      const desc = el.querySelector(".c-abstract, .c-span-last, .c-row")?.textContent?.trim()?.substring(0, 200) || "";
      results.push({ title, desc });
    });
    return results.slice(0, 10);
  });
  r4.forEach((r, i) => console.log(`${i+1}. ${r.title}\n   ${r.desc}`));
  
  // Search 5: Bilibili as an alternative for finding accounts
  console.log("\n=== SEARCH: B站 少儿图书 UP主 ===");
  await page.goto("https://www.baidu.com/s?wd=B站+少儿图书+UP主+推荐", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(3000);
  
  const r5 = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll(".result, .c-container").forEach(el => {
      const title = el.querySelector("h3, .t")?.textContent?.trim() || "";
      const desc = el.querySelector(".c-abstract, .c-span-last, .c-row")?.textContent?.trim()?.substring(0, 200) || "";
      results.push({ title, desc });
    });
    return results.slice(0, 10);
  });
  r5.forEach((r, i) => console.log(`${i+1}. ${r.title}\n   ${r.desc}`));
  
  await page.screenshot({ path: "final_search.png" });
  
  await ctx.close();
  await browser.close();
  console.log("\nDone!");
})();
