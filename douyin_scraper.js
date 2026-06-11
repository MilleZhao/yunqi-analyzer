const { chromium } = require("playwright");
const fs = require("fs");

(async () => {
  const userDataDir = "./douyin_profile";
  
  const browser = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    args: ["--disable-blink-features=AutomationControlled"],
    viewport: { width: 414, height: 896 },
    userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    locale: "zh-CN",
    isMobile: true,
    hasTouch: true
  });
  
  await browser.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => false });
    window.chrome = { runtime: {} };
  });
  
  const allResults = { videos: [], users: [] };
  
  async function searchDouyin(keyword, type) {
    const page = await browser.newPage();
    
    // Collect API responses
    const apiResponses = [];
    page.on("response", async (response) => {
      const url = response.url();
      if (url.includes("aweme") || url.includes("search") || url.includes("user")) {
        try {
          const json = await response.json();
          apiResponses.push({ url, data: json });
        } catch(e) {}
      }
    });
    
    const url = type === "user" 
      ? `https://www.douyin.com/search/${encodeURIComponent(keyword)}?type=user`
      : `https://www.douyin.com/search/${encodeURIComponent(keyword)}?type=general`;
    
    console.log(`\n=== Searching Douyin (${type}): ${keyword} ===`);
    try {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
      await page.waitForTimeout(10000);
      
      // Take screenshot
      const fname = `douyin_${keyword}_${type}.png`;
      await page.screenshot({ path: fname, fullPage: false });
      
      // Scroll to load more
      for (let i = 0; i < 3; i++) {
        await page.evaluate(() => window.scrollBy(0, 800));
        await page.waitForTimeout(2000);
      }
      
      // Extract data
      const data = await page.evaluate((t) => {
        const results = [];
        // Get all visible text in the page
        const body = document.body?.innerText || "";
        
        if (t === "general") {
          // Try to find video cards
          const cards = document.querySelectorAll('[class*="search-result-card"], [class*="video-card"], a[href*="/video/"], div[data-e2e]');
          cards.forEach(el => {
            const link = el.href || el.querySelector("a")?.href || "";
            const desc = el.querySelector('[class*="desc"], [class*="title"]')?.textContent?.trim() || "";
            const author = el.querySelector('[class*="author"], [class*="nickname"]')?.textContent?.trim() || "";
            const likes = el.querySelector('[class*="like"], [class*="count"]')?.textContent?.trim() || "";
            if (desc || author) {
              results.push({ type: "video", link, desc: desc.substring(0, 100), author, likes });
            }
          });
        } else {
          const cards = document.querySelectorAll('[class*="user-card"], [class*="account"]');
          cards.forEach(el => {
            const link = el.querySelector("a")?.href || "";
            const name = el.querySelector('[class*="name"], [class*="nickname"]')?.textContent?.trim() || "";
            const desc = el.querySelector('[class*="desc"]')?.textContent?.trim() || "";
            const fans = el.querySelector('[class*="fans"], [class*="follower"]')?.textContent?.trim() || "";
            if (name) {
              results.push({ type: "user", link, name, desc: desc.substring(0, 100), fans });
            }
          });
        }
        
        // If empty, dump all links
        if (results.length === 0) {
          document.querySelectorAll("a[href]").forEach(a => {
            const href = a.href;
            const text = a.textContent?.trim()?.substring(0, 30);
            if (href.includes("/user/") || href.includes("/video/") || href.includes("/search/")) {
              results.push({ type: "link", link: href, text });
            }
          });
        }
        
        return { results, bodyPreview: body.substring(0, 500) };
      }, type);
      
      console.log(`Results found: ${data.results.length}`);
      data.results.slice(0, 20).forEach((r, i) => {
        console.log(`${i+1}. ${JSON.stringify(r).substring(0, 200)}`);
      });
      
      // Check API responses
      if (apiResponses.length > 0) {
        console.log(`\nAPI Responses captured: ${apiResponses.length}`);
        apiResponses.slice(0, 3).forEach((r, i) => {
          console.log(`API ${i+1}: ${r.url.substring(0, 100)}`);
          const d = r.data;
          if (d) {
            const str = JSON.stringify(d).substring(0, 500);
            console.log(`  Data: ${str}`);
          }
        });
      }
      
      // Save data
      const key = type === "user" ? "users" : "videos";
      allResults[key].push({ keyword, results: data.results, apiResponses });
      
    } catch(e) {
      console.error(`Error searching ${keyword}: ${e.message}`);
    }
    
    await page.close();
  }
  
  // Search for both keywords with both types
  await searchDouyin("少儿图书", "general");
  await searchDouyin("少儿图书", "user");
  await searchDouyin("图书", "general");
  await searchDouyin("图书", "user");
  await searchDouyin("童书", "general");
  await searchDouyin("童书", "user");
  await searchDouyin("绘本推荐", "general");
  await searchDouyin("绘本推荐", "user");
  
  fs.writeFileSync("douyin_results.json", JSON.stringify(allResults, null, 2), "utf-8");
  console.log("\n\n=== ALL DOUYIN RESULTS SAVED ===");
  
  await browser.close();
  console.log("Done! Browser closed.");
})();
