# Coze 工作流 — 抖音爆款分析

## 流程图
```
[Start(Webhook)] → [Code:提取元数据] → [Code:构建Prompt] → [HTTP:DeepSeek] → [Code:解析+格式化] → [Code:写飞书] → [End]
```

## 全局变量（在工作流右上角「变量」里配）
| 变量名 | 值 |
|---|---|
| DEEPSEEK_API_KEY | sk-489a04027ef54a1fa64fa72b5ce7123a |
| FEISHU_BASE_TOKEN | RlGBbQpxBalchssDFJbcuBjGnee |
| FEISHU_TABLE_ID | tbllt7XfgHBPcdvS |
| FEISHU_APP_ID | 从飞书开放平台获取 |
| FEISHU_APP_SECRET | 从飞书开放平台获取 |

---

## Node 1: Start（Webhook 触发器）

**输入变量定义：**
| 变量名 | 类型 | JSONPath |
|---|---|---|
| url | string | $.url |
| record_id | string | $.record_id |
| 抖音链接 | string | $.抖音链接 |

---

## Node 2: Code (Python) — 提取抖音元数据

**输入：** {{Start.url}}
**输出变量：** title, author, digg_count, comment_count, share_count, collect_count, music_title, hashtags_str, description, content_type, video_id, error

```python
import json, re, requests

def main(args):
    url = args.get("url") or args.get("抖音链接") or ""
    result = {
        "title": "", "author": "", "digg_count": 0, "comment_count": 0,
        "share_count": 0, "collect_count": 0, "music_title": "",
        "hashtags_str": "", "description": "", "content_type": "video",
        "video_id": "", "error": ""
    }

    if not url:
        result["error"] = "missing url"
        return result

    # 提取 video_id
    m = re.search(r'video/(\d+)', url) or re.search(r'note/(\d+)', url)
    vid = m.group(1) if m else ""
    if not vid and re.match(r'^\d{15,20}$', url.strip()):
        vid = url.strip()
    result["video_id"] = vid

    if not vid:
        result["error"] = "cannot parse video_id"
        return result

    share_url = f"https://m.douyin.com/share/video/{vid}"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
            "Referer": "https://www.douyin.com/"
        }
        resp = requests.get(share_url, headers=headers, timeout=15, allow_redirects=True)
        html = resp.text

        # 提取 SSR 数据: window._ROUTER_DATA = {...};
        m = re.search(r'window\._ROUTER_DATA\s*=\s*(\{.*?\});', html, re.DOTALL)
        if not m:
            result["error"] = "no SSR data found (可能需要登录态)"
            return result

        data = json.loads(m.group(1))
        vp = data.get("loaderData", {}).get("video_(id)/page", {})
        vir = vp.get("videoInfoRes", {})
        items = vir.get("item_list", [])
        if not items:
            result["error"] = "empty item_list"
            return result

        item = items[0]
        author = item.get("author", {})
        music = item.get("music", {})
        stats = item.get("statistics", {})

        result["title"] = (item.get("desc") or "")[:200]
        result["description"] = (item.get("desc") or "")[:500]
        result["author"] = author.get("nickname") or ""
        result["digg_count"] = stats.get("digg_count", 0) or 0
        result["comment_count"] = stats.get("comment_count", 0) or 0
        result["share_count"] = stats.get("share_count", 0) or 0
        result["collect_count"] = stats.get("collect_count", 0) or 0
        result["music_title"] = music.get("title", "") or ""
        result["content_type"] = "video" if item.get("aweme_type") == 0 else "slideshow"
        result["duration_ms"] = item.get("duration", 0) or 0

        # 话题标签
        tags = item.get("cha_list") or []
        if not tags and (item.get("desc") or "").find("#") >= 0:
            tags = [{"name": t} for t in re.findall(r'#([^\s#]+)', item.get("desc", ""))]
        result["hashtags_str"] = " ".join(["#" + t.get("name", "") for t in tags])

    except requests.Timeout:
        result["error"] = "request timeout"
    except Exception as e:
        result["error"] = str(e)[:200]

    return result
```

## Node 3: Code (Python) — 构建 DeepSeek 分析 Prompt

**输入：** Node2 的全部输出（title, author, digg_count, comment_count, share_count, collect_count, music_title, hashtags_str, description, content_type, video_id）
**输出变量：** system_prompt, user_message

```python
def main(args):
    digg = max(args.get("digg_count", 0) or 0, 1)
    share = args.get("share_count", 0) or 0
    collect = args.get("collect_count", 0) or 0
    comment = args.get("comment_count", 0) or 0

    system_prompt = """你是一个短视频爆款分析师，专精于抖音平台的内容拆解与策略复盘。
请根据提供的素材（视频元数据），按以下六个维度逐一分析，输出结构化解析卡。

## 分析维度
### 1. 前3秒钩子
用了什么策略让用户停止滑动？钩子类型是什么（认知冲突/情绪共鸣/利益诱导/信息差/好奇/视觉冲击）？
### 2. 内容结构
视频分几个段落？每段的叙事功能是什么？
### 3. 情绪与痛点
触发了哪种情绪？戳中了什么痛点？
### 4. 拍摄/剪辑手法
镜头运用、字幕设计、BGM、节奏等技术层面的具体亮点
### 5. 行动引导（CTA）
如何引导用户点赞/评论/收藏/关注？是软引导还是硬推销？
### 6. 出版社复用建议
这个视频的核心手法如何迁移到图书/出版行业的内容创作？给出具体可操作的建议。

## 要求
- 基于视频实际内容分析，不推断，不编造
- 每个维度2-4句，简洁直接
- 第6点必须给出出版社能直接参考的具体做法

## 输出格式
```
## 1. 前3秒钩子
- 钩子策略: ...
- 钩子类型: ...
## 2. 内容结构
- 段落划分: ...
- 叙事功能: ...
## 3. 情绪与痛点
- 触发情绪: ...
- 核心痛点: ...
## 4. 拍摄/剪辑手法
- 镜头: ...
- 字幕: ...
- BGM: ...
- 节奏: ...
## 5. 行动引导（CTA）
- 引导方式: ...
- CTA类型: ...
## 6. 出版社复用建议
- 可直接复用: ...
- 需适配调整: ...
- 避坑提醒: ...
```"""

    user_message = f"""# 视频元数据
视频ID: {args.get("video_id", "")}
类型: {args.get("content_type", "video")}
标题: {args.get("title", "")}
文案: {args.get("description", "")}
作者: {args.get("author", "")}
BGM: {args.get("music_title", "")}
标签: {args.get("hashtags_str", "")}

## 互动数据
点赞: {digg}
评论: {comment}
分享: {share}
收藏: {collect}
评论/点赞: {comment/digg*100:.1f}%
分享/点赞: {share/digg*100:.1f}%
收藏/点赞: {collect/digg*100:.1f}%

注意：由于无法提取视频画面，请仅基于标题、文案、互动数据和标签进行推断分析。对于无法确定的内容（如具体镜头运用），请注明"根据数据推测"并给出合理推断。"""

    return {"system_prompt": system_prompt, "user_message": user_message}
```

## Node 4: HTTP 请求 — 调用 DeepSeek API

| 配置项 | 值 |
|---|---|
| 方法 | POST |
| URL | https://api.deepseek.com/chat/completions |
| Headers | Content-Type: application/json; Authorization: Bearer {{DEEPSEEK_API_KEY}} |
| Body (JSON) | 见下方 |
| 超时 | 120 秒 |

**Body:**
```json
{
  "model": "deepseek-chat",
  "messages": [
    {"role": "system", "content": "{{Node3.system_prompt}}"},
    {"role": "user", "content": "{{Node3.user_message}}"}
  ],
  "temperature": 0.7,
  "max_tokens": 4096
}
```

**输出提取（从响应里拿）：**
- `analysis_text` = `$.choices[0].message.content`

---

## Node 5: Code (Python) — 解析分析结果 + 格式化飞书记录

**输入：** Node4.analysis_text + Node2 的全部元数据
**输出变量：** record_json (string), grade, hook_3s, core_insight, emotion_tag

```python
import json, re

def grade_by_likes(likes):
    if likes >= 100000: return "S-超爆"
    elif likes >= 10000: return "A-大爆"
    elif likes >= 1000: return "B-小爆"
    return "C-普通"

def extract_block(text, patterns):
    for pat in patterns:
        m = re.search(pat, text, re.DOTALL)
        if m:
            raw = m.group(1).strip()
            raw = re.sub(r'✎\s*待补充[^\n]*', '', raw).strip()
            return raw[:500]
    return ""

def main(args):
    analysis = args.get("analysis_text", "")
    digg = max(args.get("digg_count", 0) or 0, 1) or 1
    share = args.get("share_count", 0) or 0
    collect = args.get("collect_count", 0) or 0
    comment = args.get("comment_count", 0) or 0

    grade = grade_by_likes(digg)

    # 提取各维度
    hook_3s = extract_block(analysis, [
        r'##\s*1\.\s*前3秒钩子.*?\n+(.+?)(?:\n##|\Z)',
        r'[-*]\s*钩子策略[：:]\s*(.+?)(?:\n[-*]|\n##|\Z)',
    ])

    content_struct = extract_block(analysis, [
        r'##\s*2\.\s*内容结构.*?\n+(.+?)(?:\n##|\Z)',
    ])

    emotion_tag = extract_block(analysis, [
        r'##\s*3\.\s*情绪与痛点.*?\n+(.+?)(?:\n##|\Z)',
        r'[-*]\s*触发情绪[：:]\s*(.+?)(?:\n[-*]|\n##|\Z)',
    ])

    core_insight = extract_block(analysis, [
        r'##\s*4\.\s*拍摄.*?\n+(.+?)(?:\n##|\Z)',
    ])

    # 钩子类型
    hook_type = ""
    if "认知冲突" in analysis: hook_type = "认知冲突"
    elif "情绪共鸣" in analysis or "情绪钩子" in analysis: hook_type = "情绪共鸣"
    elif "利益" in analysis: hook_type = "利益诱导"
    elif "视觉冲击" in analysis or "视觉钩子" in analysis: hook_type = "视觉冲击"
    elif "信息差" in analysis: hook_type = "信息差"
    elif "好奇" in analysis: hook_type = "好奇"

    # CTA 类型
    cta_type = "无"
    block_cta = extract_block(analysis, [
        r'##\s*5\.\s*行动引导.*?\n+(.+?)(?:\n##|\Z)',
    ])
    if "商品" in block_cta or "链接" in block_cta: cta_type = "商品引导"
    elif "关注" in block_cta: cta_type = "关注引导"
    elif "评论" in block_cta: cta_type = "评论区引导"
    elif "主页" in block_cta: cta_type = "主页引导"
    elif "情绪" in block_cta or "收尾" in block_cta: cta_type = "情绪收尾"

    # 可复用建议
    reuse_tip = extract_block(analysis, [
        r'##\s*6\.\s*出版社复用.*?\n+(.+?)(?:\n##|\Z)',
        r'[-*]\s*可直接复用[：:]\s*(.+?)(?:\n[-*]|\n##|\Z)',
    ]) or extract_block(analysis, [
        r'[-*]\s*可复用建议[：:]\s*(.+?)(?:\n[-*]|\Z)',
    ])

    # BGM
    music_title = args.get("music_title", "") or ""
    bgm_str = music_title if len(music_title) < 50 else music_title[:47] + "..."

    # 话题标签
    hashtags_str = args.get("hashtags_str", "") or ""

    video_id = args.get("video_id", "") or ""
    video_url = f"https://www.douyin.com/video/{video_id}" if video_id else ""

    # 构建飞书记录
    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    fields = {
        "视频ID": str(video_id),
        "视频链接": video_url,
        "标题": (args.get("title", "") or "")[:200],
        "作者": args.get("author", "") or "",
        "类型": "视频" if args.get("content_type") == "video" else "图文",
        "点赞数": digg,
        "评论数": comment,
        "分享数": share,
        "收藏数": collect,
        "爆款等级": grade,
        "前3秒钩子": hook_3s,
        "内容结构": content_struct,
        "情绪标签": emotion_tag,
        "核心洞察": core_insight,
        "钩子类型": hook_type,
        "拍摄手法": core_insight,
        "CTA类型": cta_type,
        "可复用建议": reuse_tip,
        "BGM": bgm_str,
        "话题标签": hashtags_str,
        "分析时间": now,
    }

    return {
        "record_json": json.dumps(fields, ensure_ascii=False),
        "grade": grade,
        "hook_3s": hook_3s,
        "core_insight": core_insight,
        "emotion_tag": emotion_tag,
    }
```

## Node 6: Code (Python) — 写入飞书多维表格

**输入：** Node5.record_json（字符串），以及全局变量 FEISHU_BASE_TOKEN, FEISHU_TABLE_ID, FEISHU_APP_ID, FEISHU_APP_SECRET
**输出变量：** feishu_record_id, feishu_ok

```python
import json, requests

def main(args):
    feishu_app_id = "<<FEISHU_APP_ID>>"      # 替换为实际值
    feishu_app_secret = "<<FEISHU_APP_SECRET>>"  # 替换为实际值
    base_token = "RlGBbQpxBalchssDFJbcuBjGnee"
    table_id = "tbllt7XfgHBPcdvS"
    record_json_str = args.get("record_json", "{}")

    try:
        # Step 1: 获取 tenant_access_token
        token_resp = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": feishu_app_id, "app_secret": feishu_app_secret},
            timeout=10
        )
        token_data = token_resp.json()
        access_token = token_data.get("tenant_access_token", "")
        if not access_token:
            return {"feishu_ok": False, "feishu_error": f"token failed: {token_data}"}

        # Step 2: 写入记录
        fields = json.loads(record_json_str)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/records"
        resp = requests.post(url, headers=headers, json={"fields": fields}, timeout=15)
        data = resp.json()

        if data.get("code") == 0:
            record_id = data.get("data", {}).get("record", {}).get("record_id", "")
            return {"feishu_ok": True, "feishu_record_id": record_id}
        else:
            return {"feishu_ok": False, "feishu_error": f"code={data.get('code')} msg={data.get('msg')}"}

    except Exception as e:
        return {"feishu_ok": False, "feishu_error": str(e)[:200]}
```

> ⚠️ `feishu_app_id` 和 `feishu_app_secret` 需要从飞书开放平台 (open.feishu.cn) 创建企业自建应用获取。在 Coze 工作流里建议配成全局变量，而不是硬编码在代码里。

---

## Node 7: End（结束节点）

**输出：**
```json
{
  "ok": "{{Node6.feishu_ok}}",
  "record_id": "{{Node6.feishu_record_id}}",
  "grade": "{{Node5.grade}}",
  "core_insight": "{{Node5.core_insight}}"
}
```

---

## 连线顺序
```
Start ──→ Node2(提取元数据) ──→ Node3(构建Prompt) ──→ Node4(DeepSeek) ──→ Node5(解析) ──→ Node6(写飞书) ──→ End
```

如果 Node2 返回 `error` 不为空，可以在 Node2 后面加一个 **条件分支节点**：
- 条件: `{{Node2.error}}` 不为空 → 直接跳到 End 返回错误
- 否则 → 继续 Node3
