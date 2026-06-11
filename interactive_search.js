const { chromium } = require("playwright");
const fs = require("fs");

(async () => {
  const userDataDir = "./browser_data";
  
  const browser = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    args: ["--disable-blink-features=AutomationControlled"],
    viewport: { width: 1280, height: 900 },
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    locale: "zh-CN"
  });
  
  await browser.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => false });
    window.chrome = { runtime: {} };
  });
  
  const page = await browser.newPage();
  
  // Step 1: Go to Douyin login
  console.log("Opening Douyin... Please log in if needed.");
  await page.goto("https://www.douyin.com", {
    waitUntil: "domcontentloaded",
    timeout: 60000
  });
  console.log("Douyin loaded. Current title:", await page.title());
  
  // Wait for user to login - check every 5 seconds for 2 minutes
  console.log("Waiting for login (checking for user menu)...");
  let loggedIn = false;
  for (let i = 0; i < 24; i++) {
    await page.waitForTimeout(5000);
    try {
      loggedIn = await page.evaluate(() => {
        return !!document.querySelector('[class*="user"], [class*="login"], [class*="avatar"], [class*="profile"]') &&
               !document.querySelector('[class*="login-btn"], [class*="login-mask"]');
      });
    } catch(e) {}
    if (loggedIn || i === 23) {
      if (!loggedIn) console.log("Timeout - proceeding anyway...");
      break;
    }
    console.log(`Still waiting... (${(i+1)*5}s)`);
  }
  
  // Now search for 少儿图书
  console.log("\n=== Searching Douyin: 少儿图书 ===");
  await page.goto("https://www.douyin.com/search/%E5%B0%91%E5%84%BF%E5%9B%BE%E4%B9%A6?type=general", {
    waitUntil: "domcontentloaded",
    timeout: 60000
  });
  await page.waitForTimeout(8000);
  await page.screenshot({ path: "dy_children_result.png" });
  
  // Try to extract video/account info
  const dyData = await page.evaluate(() => {
    const results = [];
    // Try various selectors for search results
    const items = document.querySelectorAll('[data-e2e="search-result-item"], [class*="search-result-card"], [class*="video-card"], [class*="card-item"]');
    items.forEach(el => {
      const text = el.textContent?.trim()?.substring(0, 300) || "";
      const link = el.querySelector("a")?.href || "";
      if (text.length > 10) results.push({ text, link });
    });
    if (results.length === 0) {
      // Fallback: grab all visible text in search results area
      const container = document.querySelector('[class*="search-result"], [class*="search-list"], [class*="result-list"]');
      if (container) {
        results.push({ text: container.innerText?.substring(0, 2000) || "", link: "" });
      }
    }
    return results;
  });
  
  console.log(`Found ${dyData.length} items`);
  dyData.slice(0, 15).forEach((d, i) => {
    console.log(`${i+1}. ${d.text.substring(0, 150)}...`);
    if (d.link) console.log(`   Link: ${d.link}`);
  });
  
  // Also search for users
  console.log("\n=== Searching Douyin Users: 少儿图书 ===");
  await page.goto("https://www.douyin.com/search/%E5%B0%91%E5%84%BF%E5%9B%BE%E4%B9%A6?type=user", {
    waitUntil: "domcontentloaded",
    timeout: 60000
  });
  await page.waitForTimeout(8000);
  await page.screenshot({ path: "dy_children_users.png" });
  
  const dyUsers = await page.evaluate(() => {
    const results = [];
    const items = document.querySelectorAll('[class*="user-card"], [class*="search-user"], [class*="account-item"]');
    items.forEach(el => {
      const name = el.querySelector('[class*="name"], [class*="nickname"], [class*="title"]')?.textContent?.trim() || "";
      const desc = el.querySelector('[class*="desc"], [class*="bio"]')?.textContent?.trim() || "";
      const link = el.querySelector("a")?.href || "";
      if (name) results.push({ name, desc, link });
    });
    if (results.length === 0) {
      const container = document.querySelector('[class*="search-result"], [class*="search-list"]');
      if (container) results.push({ name: container.innerText?.substring(0, 2000) || "", desc: "", link: "" });
    }
    return results;
  });
  
  console.log(`Found ${dyUsers.length} users`);
  dyUsers.slice(0, 15).forEach((u, i) => {
    console.log(`${i+1}. ${u.name}`);
    if (u.desc) console.log(`   ${u.desc.substring(0, 100)}`);
    if (u.link) console.log(`   ${u.link}`);
  });
  
  // Now try Xiaohongshu
  console.log("\n\n=== Opening Xiaohongshu ===");
  await page.goto("https://www.xiaohongshu.com", {
    waitUntil: "domcontentloaded",
    timeout: 60000
  });
  await page.waitForTimeout(5000);
  console.log("XHS loaded. Please log in if needed.");
  
  // Wait for login
  console.log("Waiting for Xiaohongshu login...");
  for (let i = 0; i < 24; i++) {
    await page.waitForTimeout(5000);
    try {
      const isLoggedIn = await page.evaluate(() => {
        const body = document.body?.innerText || "";
        return !body.includes("登录后推荐") && !body.includes("手机号登录");
      });
      if (isLoggedIn || i === 23) {
        if (!isLoggedIn) console.log("Timeout - proceeding anyway...");
        break;
      }
    } catch(e) {}
    console.log(`Still waiting... (${(i+1)*5}s)`);
  }
  
  // Search Xiaohongshu
  console.log("\n=== Searching Xiaohongshu: 少儿图书 ===");
  await page.goto("https://www.xiaohongshu.com/search_result?keyword=%E5%B0%91%E5%84%BF%E5%9B%BE%E4%B9%A6", {
    waitUntil: "domcontentloaded",
    timeout: 60000
  });
  await page.waitForTimeout(8000);
  await page.screenshot({ path: "xhs_children_result.png" });
  
  const xhsData = await page.evaluate(() => {
    const results = [];
    const items = document.querySelectorAll('[class*="note-item"], section.note-item, [class*="card"]');
    items.forEach(el => {
      const text = el.textContent?.trim()?.substring(0, 200) || "";
      const link = el.querySelector("a")?.href || "";
      if (text.length > 10) results.push({ text, link });
    });
    if (results.length === 0) {
      const container = document.querySelector('[class*="feeds"], [class*="search-result"]');
      if (container) results.push({ text: container.innerText?.substring(0, 2000) || "", link: "" });
    }
    return results;
  });
  
  console.log(`Found ${xhsData.length} XHS items`);
  xhsData.slice(0, 15).forEach((d, i) => {
    console.log(`${i+1}. ${d.text.substring(0, 150)}...`);
    if (d.link) console.log(`   Link: ${d.link}`);
  });
  
  // Save all results
  const allResults = {
    douyin_videos: dyData,
    douyin_users: dyUsers,
    xiaohongshu: xhsData
  };
  fs.writeFileSync("platform_results.json", JSON.stringify(allResults, null, 2), "utf-8");
  
  console.log("\n\n=== ALL DONE ===");
  console.log("Results saved to platform_results.json");
  console.log("Browser will stay open. Close it when done.");
  
  // Keep browser open
  await new Promise(() => {});
})();
