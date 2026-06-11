import sys, json, os
sys.stdout.reconfigure(encoding="utf-8")

workdir = r"WORKDIR"

with open(os.path.join(workdir, "links_parsed.json"), "r", encoding="utf-8") as f:
    links_data = json.load(f)

with open(os.path.join(workdir, "douyin_results.json"), "r", encoding="utf-8") as f:
    dy_raw = json.load(f)

# Build Douyin accounts from scraped data
children_accounts = []
general_accounts = []
seen_uids = set()

for group in dy_raw.get("videos", []):
    for api in group.get("apiResponses", []):
        d = api.get("data", {})
        for bd in d.get("business_data", []):
            info = None
            bdata = bd.get("data", {})
            if bdata.get("aweme_info"):
                info = bdata["aweme_info"]
            elif bdata.get("user_info"):
                info = bdata["user_info"]
            if info:
                author = info.get("author", info)
                uid = author.get("uid", "")
                if uid and uid not in seen_uids:
                    seen_uids.add(uid)
                    acc = {
                        "nickname": author.get("nickname", "") or author.get("unique_id", ""),
                        "uid": uid,
                        "signature": (author.get("signature", "") or "").strip().replace("\n", " | "),
                        "link": f"https://www.douyin.com/user/{author.get('sec_uid', uid)}"
                    }
                    combined = acc["nickname"] + " " + acc["signature"]
                    children_kw = ["童书","少儿","儿童","绘本","小朋友","宝宝","育儿","早教","幼儿","亲子","妈妈","麻麻","爸爸","养娃","伴读","园长","小学生","启蒙","教小学"]
                    shop_kw = ["专营店","旗舰店","书店","图书店","童学"]
                    key_names = ["青葫芦","小爱童年","老夏挑绘本","安东尼","爱读书的硕硕","米团妈妈","叶子老师","安安小朋友","甜甜园长","开心鱼头","嘟嘟妈","恺欣麻麻","海宝兄弟","海淀大牛","深圳童学","烁妈伴读","三小辫儿园长","悦悦麻麻","大琪是来宝妈","鹏妈陪读","三宝说英语","央视网阅读","喜哥图书店","维乾图书","小嘉啊"]
                    is_children = any(kw in combined for kw in children_kw) or any(kw in acc["nickname"] for kw in key_names) or any(kw in combined for kw in shop_kw)
                    if is_children:
                        children_accounts.append(acc)
                    else:
                        general_accounts.append(acc)

md = []
md.append("# 少儿图书 / 图书 相关账号与链接汇总")
md.append("")
md.append("> 数据来源：小红书 + 抖音  |  2026年6月9日")
md.append("")

# === 小红书 ===
md.append("---")
md.append("")
md.append("## 小红书")
md.append("")

# 少儿童书
xhs_c = links_data["xhs_children"]
md.append("### 少儿童书")
md.append("")
for item in xhs_c:
    label = item["account"] if item["account"] else "小红书链接"
    md.append(f"- **{label}**")
    if item.get("desc"):
        md.append(f"  > {item['desc'][:120]}")
    md.append(f"  [{item['url']}]({item['url']})")
    md.append("")

# 图书
xhs_b = links_data["xhs_books"]
md.append("### 图书")
md.append("")
for item in xhs_b:
    label = item["account"] if item["account"] else "小红书链接"
    md.append(f"- **{label}**")
    if item.get("desc"):
        md.append(f"  > {item['desc'][:120]}")
    md.append(f"  [{item['url']}]({item['url']})")
    md.append("")

# === 抖音账号 ===
md.append("---")
md.append("")
md.append("## 抖音 — 搜到的账号")
md.append("")

md.append("### 少儿童书 / 童书 / 绘本 相关账号")
md.append("")
for acc in children_accounts:
    sig = acc.get("signature", "")[:120]
    md.append(f"- **{acc['nickname']}**")
    if sig:
        md.append(f"  > {sig}")
    md.append(f"  [{acc['link']}]({acc['link']})")
    md.append("")

md.append("### 图书 / 阅读 相关账号")
md.append("")
for acc in general_accounts:
    sig = acc.get("signature", "")[:120]
    md.append(f"- **{acc['nickname']}**")
    if sig:
        md.append(f"  > {sig}")
    md.append(f"  [{acc['link']}]({acc['link']})")
    md.append("")

# === 抖音视频链接 ===
md.append("---")
md.append("")
md.append("## 抖音 — 视频链接")
md.append("")

dy_c = links_data["dy_children"]
if dy_c:
    md.append("### 少儿童书 视频")
    md.append("")
    for item in dy_c:
        desc = item.get("desc", "")[:120]
        md.append(f"- [{item['url']}]({item['url']})")
        if desc:
            md.append(f"  > {desc}")
        md.append("")

dy_b = links_data["dy_books"]
if dy_b:
    md.append("### 图书 视频")
    md.append("")
    for item in dy_b:
        desc = item.get("desc", "")[:120]
        md.append(f"- [{item['url']}]({item['url']})")
        if desc:
            md.append(f"  > {desc}")
        md.append("")

output = "\n".join(md)
out_path = os.path.join(workdir, "账号链接汇总.md")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(output)

print(f"Saved: {out_path}")
print(f"Lines: {len(md)}")
