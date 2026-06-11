const { chromium } = require("playwright");
const fs = require("fs");

(async () => {
  const browser = await chromium.launch({
    headless: false,
    args: [
      "--disable-blink-features=AutomationControlled",
      "--no-sandbox",
      "--disable-web-security"
    ]
  });
  
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    locale: "zh-CN"
  });
  
  // Override navigator.webdriver
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => false });
    window.chrome = { runtime: {} };
  });
  
  const page = await ctx.newPage();
  const keyword = "少儿图书";
  
  // Try Douyin first
  console.log("Opening Douyin search...");
  try {
    await page.goto(`https://www.douyin.com/search/${encodeURIComponent(keyword)}`, {
      waitUntil: "domcontentloaded",
      timeout: 60000
    });
    console.log("Douyin page loaded, waiting for content...");
    await page.waitForTimeout(8000);
    await page.screenshot({ path: "douyin_result.png", fullPage: false });
    console.log("Douyin screenshot saved.");
    
    // Try to scroll and get content
    const content = await page.content();
    fs.writeFileSync("douyin_page.html", content, "utf-8");
    
    // Extract links
    const links = await page.evaluate(() => {
      const results = [];
      const anchors = document.querySelectorAll("a[href]");
      anchors.forEach(a => {
        const href = a.href;
        const text = a.textContent?.trim()?.substring(0, 50);
        if (href && (href.includes("/video/") || href.includes("/user/"))) {
          results.push({ href, text });
        }
      });
      return results.slice(0, 20);
    });
    
    console.log("\n=== DOUYIN LINKS ===");
    links.forEach((l, i) => console.log(`${i+1}. ${l.href} - ${l.text}`));
    fs.writeFileSync("douyin_links.json", JSON.stringify(links, null, 2), "utf-8");
    
  } catch(e) {
    console.error("Douyin error:", e.message);
    await page.screenshot({ path: "douyin_error.png" });
  }
  
  await ctx.close();
  await browser.close();
  console.log("\nDone!");
})();
