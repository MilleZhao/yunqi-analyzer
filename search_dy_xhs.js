const { chromium } = require("playwright");
const fs = require("fs");

(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = {};

  async function searchXHS(keyword) {
    const ctx = await browser.newContext({
      viewport: { width: 1280, height: 900 },
      userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      locale: "zh-CN"
    });
    const page = await ctx.newPage();
    const url = `https://www.xiaohongshu.com/search_result?keyword=${encodeURIComponent(keyword)}&source=web_search_result_notes`;
    console.log(`[XHS] Opening: ${url}`);
    try {
      await page.goto(url, { waitUntil: "networkidle", timeout: 45000 });
      await page.waitForTimeout(5000);
      
      // Take screenshot
      const fname = `xhs_${keyword}.png`;
      await page.screenshot({ path: fname, fullPage: false });
      
      // Try to extract data
      const data = await page.evaluate(() => {
        const items = [];
        // Try multiple selectors
        const cards = document.querySelectorAll('[class*="note-item"], [class*="card"], [class*="search-result"] a[href*="/explore/"], a[href*="/explore/"], section.note-item, .feeds-page .note-item');
        cards.forEach((el, i) => {
          const href = el.href || el.querySelector("a")?.href || "";
          const title = el.querySelector('[class*="title"], [class*="desc"], .title, .note-text')?.textContent?.trim() || "";
          const author = el.querySelector('[class*="author"], [class*="name"], .author .name, .nickname')?.textContent?.trim() || "";
          const likes = el.querySelector('[class*="like"], [class*="count"]')?.textContent?.trim() || "";
          if (href || title || author) {
            items.push({ href, title, author, likes });
            if (items.length >= 20) return;
          }
        });
        return items;
      });
      
      results[`xiaohongshu_${keyword}`] = data;
      console.log(`[XHS] Found ${data.length} items for "${keyword}"`);
    } catch(e) {
      console.error(`[XHS] Error for "${keyword}": ${e.message}`);
      const fname = `xhs_${keyword}_error.png`;
      await page.screenshot({ path: fname, fullPage: false });
    }
    await ctx.close();
  }

  async function searchDY(keyword) {
    const ctx = await browser.newContext({
      viewport: { width: 1280, height: 900 },
      userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      locale: "zh-CN"
    });
    const page = await ctx.newPage();
    const url = `https://www.douyin.com/search/${encodeURIComponent(keyword)}`;
    console.log(`[DY] Opening: ${url}`);
    try {
      await page.goto(url, { waitUntil: "networkidle", timeout: 45000 });
      await page.waitForTimeout(5000);
      
      const fname = `dy_${keyword}.png`;
      await page.screenshot({ path: fname, fullPage: false });
      
      const data = await page.evaluate(() => {
        const items = [];
        const cards = document.querySelectorAll('[class*="search-result"], [class*="video-card"], a[href*="/video/"], [data-e2e*="search"], [class*="card"]');
        cards.forEach((el, i) => {
          const href = el.href || el.querySelector("a")?.href || "";
          const title = el.querySelector('[class*="title"], [class*="desc"]')?.textContent?.trim() || "";
          const author = el.querySelector('[class*="author"], [class*="name"], [class*="nickname"]')?.textContent?.trim() || "";
          const likes = el.querySelector('[class*="like"], [class*="count"]')?.textContent?.trim() || "";
          if (href || title || author) {
            items.push({ href, title, author, likes });
            if (items.length >= 20) return;
          }
        });
        return items;
      });
      
      results[`douyin_${keyword}`] = data;
      console.log(`[DY] Found ${data.length} items for "${keyword}"`);
    } catch(e) {
      console.error(`[DY] Error for "${keyword}": ${e.message}`);
      const fname = `dy_${keyword}_error.png`;
      await page.screenshot({ path: fname, fullPage: false });
    }
    await ctx.close();
  }

  await searchXHS("少儿图书");
  await searchDY("少儿图书");
  await searchXHS("图书");
  await searchDY("图书");

  fs.writeFileSync("search_results.json", JSON.stringify(results, null, 2), "utf-8");
  console.log("\n=== RESULTS ===");
  for (const [key, items] of Object.entries(results)) {
    console.log(`\n--- ${key} (${items.length} results) ---`);
    items.slice(0, 10).forEach((item, i) => {
      console.log(`${i+1}. ${item.title || "(no title)"}`);
      console.log(`   Author: ${item.author || "unknown"}`);
      console.log(`   Link: ${item.href || "n/a"}`);
      console.log(`   Likes: ${item.likes || "n/a"}`);
    });
  }

  await browser.close();
  console.log("\nDone! Screenshots and results saved.");
})();
