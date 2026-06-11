/**
 * 抖音单视频内容提取器 v4
 * SSR 提取 + 多类型支持 + 并行提速
 *
 * 用法:
 *   node extract_single.js <抖音链接> [--no-video] [--headless]
 * 提速: 视频URL竞速下载, 幻灯片并发下载, 缩短冗余等待
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const https = require("https");
const http = require("http");

const TARGET_INPUT = process.argv[2];
const SKIP_VIDEO = process.argv.includes("--no-video");
const HEADLESS = process.argv.includes("--headless");

if (!TARGET_INPUT) { console.error("用法: node extract_single.js <链接|ID> [--no-video] [--headless]"); process.exit(1); }

const WORKDIR = __dirname;
const PROFILE_DIR = path.join(WORKDIR, "douyin_profile");

function downloadFile(url, destPath, timeoutMs = 120000) {
  return new Promise((resolve, reject) => {
    const proto = url.startsWith("https") ? https : http;
    const file = fs.createWriteStream(destPath);
    const req = proto.get(url, { headers: { "User-Agent": "Mozilla/5.0", "Referer": "https://www.douyin.com/" }, timeout: timeoutMs }, (res) => {
      if ([301,302,307,308].includes(res.statusCode) && res.headers.location) {
        file.close(); try{fs.unlinkSync(destPath)}catch(_){};
        return downloadFile(res.headers.location, destPath, timeoutMs).then(resolve).catch(reject);
      }
      if (res.statusCode >= 400) { file.close(); try{fs.unlinkSync(destPath)}catch(_){}; return reject(new Error("HTTP "+res.statusCode)); }
      res.pipe(file); file.on("finish",()=>{file.close();resolve()}); file.on("error",reject);
    });
    req.on("error", reject);
    req.on("timeout", () => { req.destroy(); file.close(); try{fs.unlinkSync(destPath)}catch(_){}; reject(new Error("timeout")); });
  });
}

function downloadRace(urls, destPath, minSize, timeoutMs) {
  minSize = minSize || 10000; timeoutMs = timeoutMs || 60000;
  if (!urls || urls.length === 0) return Promise.resolve(false);
  return new Promise((resolve) => {
    let settled = false;
    const parts = urls.slice(0, 3).map(function(u, i) { return destPath + ".part" + i; });
    let done = 0;

    function cleanup() {
      for (var j = 0; j < parts.length; j++) { try { fs.unlinkSync(parts[j]); } catch (_) {} }
    }

    for (let i = 0; i < Math.min(urls.length, 3); i++) {
      downloadFile(urls[i], parts[i], timeoutMs).then(function() {
        if (settled) return;
        try {
          if (fs.statSync(parts[i]).size > minSize) {
            settled = true;
            fs.renameSync(parts[i], destPath);
            setTimeout(cleanup, 100);
            resolve(true);
            return;
          }
        } catch (_) {}
        done++;
        if (done >= Math.min(urls.length, 3) && !settled) { cleanup(); resolve(false); }
      }).catch(function() {
        done++;
        if (done >= Math.min(urls.length, 3) && !settled) { cleanup(); resolve(false); }
      });
    }
  });
}

function parseHashtags(desc) {
  const tags = [];
  const re = /#([^\s#]+)/g;
  let m;
  while ((m = re.exec(desc)) !== null) {
    tags.push({ id: "", name: m[1] });
  }
  return tags;
}

(async function() {
  console.log("\n=== 抖音单视频提取 v4 ===");
  var t0 = Date.now();

  var targetUrl = TARGET_INPUT.trim();
  var videoId = "";
  var m1 = targetUrl.match(/video\/(\d+)/);
  var m2 = targetUrl.match(/note\/(\d+)/);
  if (m1) videoId = m1[1];
  else if (m2) videoId = m2[1];
  else if (/^\d{15,20}$/.test(targetUrl)) videoId = targetUrl;
  console.log("Video ID:", videoId || "(待解析)");

  var browser = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: HEADLESS,
    args: ["--disable-blink-features=AutomationControlled"],
    viewport: { width: 414, height: 896 },
    userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    locale: "zh-CN", isMobile: true, hasTouch: true,
  });
  await browser.addInitScript(function() {
    Object.defineProperty(navigator, "webdriver", { get: function() { return false; } });
    window.chrome = { runtime: {} };
  });

  var page = await browser.newPage();
  var shareUrl = videoId ? "https://m.douyin.com/share/video/" + videoId : targetUrl;

  console.log("[导航]", shareUrl);
  try { await page.goto(shareUrl, { waitUntil: "domcontentloaded", timeout: 60000 }); }
  catch(e) { console.log("[导航] 超时"); }
  
  // 等待 SSR 数据就绪
  try {
    await page.waitForFunction(function() {
      var rd = window._ROUTER_DATA;
      if (!rd) return false;
      var vp = rd.loaderData && rd.loaderData["video_(id)/page"];
      return vp && vp.videoInfoRes && vp.videoInfoRes.item_list && vp.videoInfoRes.item_list.length > 0;
    }, { timeout: 15000 });
    console.log("[就绪]", Date.now() - t0, "ms");
  } catch(e) {
    console.log("[就绪] 等待超时，尝试兜底读取...");
    await page.waitForTimeout(2000);
  }

  var finalUrl = page.url();
  var finalMatch = finalUrl.match(/video\/(\d+)/) || finalUrl.match(/note\/(\d+)/);
  if (!videoId && finalMatch) videoId = finalMatch[1];
  if (!videoId) videoId = TARGET_INPUT.replace(/\D/g,"").slice(0,19);
  console.log("[页面] Video ID:", videoId);

  var pageData = await page.evaluate(function() {
    var rd = window._ROUTER_DATA;
    if (!rd) return null;
    var vp = (rd.loaderData || {})["video_(id)/page"] || {};
    var vir = vp.videoInfoRes || {};
    return (vir.item_list || [])[0] || null;
  });

  if (!pageData) {
    console.error("[错误] 未提取到数据。可能未登录。");
    await browser.close();
    process.exit(1);
  }

  var author = pageData.author || {};
  var music = pageData.music || {};
  var video = pageData.video || {};
  var stats = pageData.statistics || {};
  var awemeType = pageData.aweme_type;
  var contentType = (awemeType === 0) ? "video" : "slideshow";
  var descText = pageData.desc || "";
  var hashtags = (pageData.cha_list || []).map(function(c) { return { id: c.cid || "", name: c.cha_name || "" }; });
  if (hashtags.length === 0 && descText.includes("#")) {
    hashtags = parseHashtags(descText);
  }

  var metadata = {
    source_url: targetUrl, resolved_url: finalUrl, video_id: videoId,
    extracted_at: new Date().toISOString(),
    content_type: contentType, aweme_type: awemeType,
    title: descText, description: descText,
    duration_ms: pageData.duration || 0, create_time: pageData.create_time || 0,
    author: {
      uid: author.uid || "", sec_uid: author.sec_uid || "",
      nickname: author.nickname || author.unique_id || "",
      signature: (author.signature || "").replace(/\n/g, " | "),
      avatar_urls: ((author.avatar_thumb || author.avatar_medium || {}).url_list || []).slice(0, 2),
      homepage: "https://www.douyin.com/user/" + (author.sec_uid || author.uid || ""),
    },
    music: {
      id: music.id || music.id_str || "", title: music.title || "", author: music.author || "",
      duration: music.duration || 0,
      cover_urls: ((music.cover_thumb || music.cover_medium || {}).url_list || []).slice(0, 2),
      play_url: ((music.play_url || {}).url_list || [])[0] || "",
    },
    hashtags: hashtags,
    statistics: {
      digg_count: stats.digg_count || 0, comment_count: stats.comment_count || 0,
      share_count: stats.share_count || 0, collect_count: stats.collect_count || 0,
      play_count: stats.play_count || 0,
    },
    video_urls: (video.play_addr || {}).url_list || [],
    download_urls: (video.download_addr || {}).url_list || [],
    cover_urls: (video.cover || {}).url_list || [],
    origin_cover_urls: (video.origin_cover || {}).url_list || [],
    dynamic_cover_urls: (video.dynamic_cover || {}).url_list || [],
    has_watermark: video.has_watermark || false,
    bit_rates: (video.bit_rate || []).map(function(br) {
      return { name: br.gear_name || "", quality: br.quality_type || 0, fps: br.FPS || 0, urls: ((br.play_addr || {}).url_list || []).slice(0, 2) };
    }),
    images: pageData.image_infos ? Object.values(pageData.image_infos).map(function(img) {
      return { urls: ((img.label_large || img.label_middle || {}).url_list || []).slice(0, 2), width: img.width || 0, height: img.height || 0 };
    }) : [],
  };

  var outDir = path.join(WORKDIR, "extracted", videoId);
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, "metadata.json"), JSON.stringify(metadata, null, 2), "utf-8");
  console.log("[保存] metadata.json");

  var coverUrl = metadata.cover_urls[0] || metadata.origin_cover_urls[0];
  if (coverUrl) { try { await downloadFile(coverUrl, path.join(outDir, "cover.jpg")); console.log("[下载] cover.jpg"); } catch(e) {} }

  var videoPath = null;
  if (!SKIP_VIDEO && contentType === "video") {
    var urls = metadata.bit_rates.filter(function(b){return b.name==="adapt_1080_0"||b.name==="adapt_720_0"}).flatMap(function(b){return b.urls})
      .concat(metadata.video_urls).concat(metadata.download_urls).filter(Boolean);
    videoPath = path.join(outDir, "video.mp4");
    var ok = await downloadRace(urls, videoPath, 10000, 60000);
    if (ok) {
      try { console.log("[下载] video.mp4", (fs.statSync(videoPath).size/1024/1024).toFixed(1), "MB"); } catch(_) {}
    } else {
      console.log("[下载] 视频下载失败");
      videoPath = null;
    }
  } else if (!SKIP_VIDEO && metadata.images.length > 0) {
    var slideDownloads = metadata.images.map(function(img, i) {
      if (img.urls.length > 0) {
        return downloadFile(img.urls[0], path.join(outDir, "slide_" + String(i+1).padStart(2,"0") + ".jpg")).catch(function(){});
      }
      return Promise.resolve();
    });
    await Promise.all(slideDownloads);
    console.log("[下载]", metadata.images.length, "张幻灯片");
  }
  
  if (contentType === "slideshow" && metadata.images.length === 0) {
    console.log("[DOM] 尝试提取幻灯片图片...");
    try {
      await page.waitForTimeout(1500);
      var domImages = await page.evaluate(function() {
        var imgs = [];
        document.querySelectorAll("img[src*='douyinpic.com'], img[src*='p3-sign'], img[src*='tos-cn']").forEach(function(el) {
          var src = el.src || el.getAttribute("data-src") || "";
          if (src && !imgs.find(function(i){ return i === src; })) imgs.push(src);
        });
        document.querySelectorAll("[class*='slide'] img, [class*='swiper'] img, [class*='carousel'] img").forEach(function(el) {
          var src = el.src || el.getAttribute("data-src") || "";
          if (src && !imgs.find(function(i){ return i === src; })) imgs.push(src);
        });
        return imgs.slice(0, 20);
      });
      if (domImages.length > 0) {
        console.log("[DOM]  found " + domImages.length + " slide images");
        metadata.images = domImages.map(function(url) { return { urls: [url], width: 0, height: 0 }; });
        var domDownloads = domImages.map(function(url, i) {
          return downloadFile(url, path.join(outDir, "slide_" + String(i+1).padStart(2,"0") + ".jpg")).catch(function(){});
        });
        await Promise.all(domDownloads);
      } else {
        console.log("[DOM]  no slide images found");
      }
    } catch(e) {
      console.log("[DOM]  failed:", e.message);
    }
  }

  var elapsed = Date.now() - t0;
  console.log("\n========== 提取摘要 ==========");
  console.log("类型:", contentType === "video" ? "视频" : "图文 (aweme_type=" + awemeType + ")");
  console.log("文案:", (descText || "(无)").substring(0, 100));
  console.log("作者:", metadata.author.nickname);
  console.log("BGM:", (metadata.music.title || "无"), "-", metadata.music.author || "");
  console.log("标签:", metadata.hashtags.map(function(h) { return "#" + h.name; }).join(" ") || "(无)");
  console.log("互动: 点赞" + metadata.statistics.digg_count + " 评论" + metadata.statistics.comment_count + " 分享" + metadata.statistics.share_count + " 收藏" + metadata.statistics.collect_count);
  console.log("耗时:", elapsed + "ms");

  process.stdout.write("\nEXTRACTED_DIR=" + outDir + "\n");
  process.stdout.write("VIDEO_PATH=" + (videoPath || "none") + "\n");

  await browser.close();
  console.log("[完成]", outDir);
})();
