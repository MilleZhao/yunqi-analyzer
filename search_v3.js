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
  
  // Search Baidu for Douyin children's book accounts
  console.log("=== SEARCHING BAIDU: 抖音 少儿图书 ===");
  await page.goto("https://www.baidu.com/s?wd=抖音+少儿图书+账号", {
    waitUntil: "domcontentloaded",
    timeout: 30000
  });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: "baidu_douyin_children.png" });
  
  const baiduResults1 = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll(".result, .c-container").forEach(el => {
      const title = el.querySelector("h3, .t")?.textContent?.trim() || "";
      const link = el.querySelector("a")?.href || "";
      const desc = el.querySelector(".c-abstract, .c-span-last")?.textContent?.trim() || "";
      results.push({ title, link, desc });
    });
    return results.slice(0, 15);
  });
  
  console.log("Baidu results for 抖音 少儿图书:");
  baiduResults1.forEach((r, i) => console.log(`${i+1}. ${r.title}\n   ${r.link}\n   ${r.desc}`));
  
  // Search for Xiaohongshu
  await page.goto("https://www.baidu.com/s?wd=小红书+少儿图书+账号", {
    waitUntil: "domcontentloaded",
    timeout: 30000
  });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: "baidu_xhs_children.png" });
  
  const baiduResults2 = await page.evaluate(() => {
    const results = [];
    document.querySelectorAll(".result, .c-container").forEach(el => {
      const title = el.querySelector("h3, .t")?.textContent?.trim() || "";
      const link = el.querySelector("a")?.href || "";
      const desc = el.querySelector(".c-abstract, .c-span-last")?.textContent?.trim() || "";
      results.push({ title, link, desc });
    });
    return results.slice(0, 15);
  });
  
  console.log("\nBaidu results for 小红书 少儿图书:");
  baiduResults2.forEach((r, i) => console.log(`${i+1}. ${r.title}\n   ${r.link}\n   ${r.desc}`));
  
  // Now try Xiaohongshu directly with a different approach
  await page.goto("https://www.xiaohongshu.com/search_result?keyword=%E5%B0%91%E5%84%BF%E5%9B%BE%E4%B9%A6", {
    waitUntil: "domcontentloaded",
    timeout: 30000
  });
  await page.waitForTimeout(5000);
  await page.screenshot({ path: "xhs_direct.png" });
  
  // Try to get data from API
  const xhsData = await page.evaluate(() => {
    // Try to find any structured data
    const items = [];
    // Look for note cards
    const noteItems = document.querySelectorAll("[class*='note-item'], section.note-item, div[class*='note']");
    noteItems.forEach(el => {
      const text = el.textContent?.trim()?.substring(0, 100);
      if (text && text.length > 5) items.push(text);
    });
    return items;
  });
  
  console.log("\n=== XHS Direct Data ===");
  xhsData.forEach((d, i) => console.log(`${i+1}. ${d}`));
  
  // Try Douyin with API approach
  await page.goto("https://www.douyin.com/search/%E5%B0%91%E5%84%BF%E5%9B%BE%E4%B9%A6?type=user", {
    waitUntil: "domcontentloaded",
    timeout: 30000
  });
  await page.waitForTimeout(5000);
  await page.screenshot({ path: "douyin_user_search.png" });
  
  const dyData = await page.evaluate(() => {
    const items = [];
    document.querySelectorAll("[class*='search-user'], [class*='user-card'], [class*='account']").forEach(el => {
      const text = el.textContent?.trim()?.substring(0, 200);
      if (text && text.length > 3) items.push(text);
    });
    return items;
  });
  
  console.log("\n=== Douyin User Search Data ===");
  dyData.forEach((d, i) => console.log(`${i+1}. ${d}`));
  
  await ctx.close();
  await browser.close();
  console.log("\nDone! All screenshots saved.");
})();
