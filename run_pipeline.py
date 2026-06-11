
"""
抖音视频 -> 爆款分析 全流程管线 v3
用法: python run_pipeline.py <抖音链接> [--headless] [--no-video]
管线结束自动: 生成中文分析骨架 + 打印元数据摘要 + 打开关键帧拼贴图
"""
import sys, os, json, subprocess, glob, webbrowser

WORKDIR = os.path.dirname(os.path.abspath(__file__))
HEADLESS = "--headless" in sys.argv

def run_step(cmd, desc):
    bar = "=" * 60
    print(f"\n{bar}\n>>> {desc}\n>>> {' '.join(cmd)}\n{bar}")
    result = subprocess.run(cmd, cwd=WORKDIR)
    return result.returncode == 0

def build_llm_input(extracted_dir):
    meta_path = os.path.join(extracted_dir, "metadata.json")
    prompt_path = os.path.join(WORKDIR, "viral_analysis_prompt.txt")
    if not os.path.exists(meta_path): return None
    with open(meta_path, "r", encoding="utf-8") as f: meta = json.load(f)
    with open(prompt_path, "r", encoding="utf-8") as f: prompt = f.read()

    cover = os.path.join(extracted_dir, "cover.jpg")
    kf_dir = os.path.join(extracted_dir, "keyframes")
    frames = sorted(glob.glob(os.path.join(kf_dir, "frame_*.jpg")))
    mosaic = os.path.join(kf_dir, "_mosaic.jpg")

    llm_input = {
        "system_prompt": prompt,
        "content_metadata": {
            "video_id": meta.get("video_id"),
            "content_type": meta.get("content_type"),
            "title": meta.get("title"),
            "description": meta.get("description")
        },
        "creator": {
            "nickname": meta.get("author",{}).get("nickname"),
            "signature": meta.get("author",{}).get("signature"),
            "homepage": meta.get("author",{}).get("homepage")
        },
        "music": {
            "title": meta.get("music",{}).get("title"),
            "author": meta.get("music",{}).get("author")
        },
        "hashtags": [h.get("name") for h in meta.get("hashtags",[])],
        "engagement": meta.get("statistics",{}),
        "assets": {
            "cover_path": cover if os.path.exists(cover) else None,
            "keyframes_dir": kf_dir,
            "keyframe_count": len(frames),
            "mosaic_path": mosaic if os.path.exists(mosaic) else None
        }
    }
    with open(os.path.join(extracted_dir, "llm_input.json"), "w", encoding="utf-8") as f:
        json.dump(llm_input, f, ensure_ascii=False, indent=2)

    md = [prompt, "", "---", "", "# 内容数据", "",
          f"- 视频ID: {meta.get('video_id')}",
          f"- 类型: {meta.get('content_type')}",
          f"- 文案: {meta.get('description','(无)')}"]
    tags = " ".join(["#"+h["name"] for h in meta.get("hashtags",[])])
    md.append(f"- 标签: {tags if tags else '(无)'}")
    md += ["", "# 创作者", "",
           f"- 昵称: {meta['author']['nickname']}",
           f"- 签名: {meta['author']['signature']}",
           f"- 主页: {meta['author']['homepage']}",
           "", "# BGM", "",
           f"- 曲名: {meta['music']['title']}",
           f"- 作者: {meta['music']['author']}",
           "", "# 互动数据", "",
           f"- 点赞: {meta['statistics']['digg_count']} | 评论: {meta['statistics']['comment_count']} | 分享: {meta['statistics']['share_count']} | 收藏: {meta['statistics']['collect_count']}",
           "", "# 视觉素材", ""]
    if os.path.exists(cover):
        md += ["## 封面", "", "![cover](../cover.jpg)", ""]
    if frames:
        md += [f"## 关键帧 ({len(frames)} 张)", ""]
        md += [f"![{os.path.basename(f)}](../keyframes/{os.path.basename(f)})" for f in sorted(frames)] + [""]
    with open(os.path.join(extracted_dir, "llm_input.md"), "w", encoding="utf-8-sig") as f:
        f.write("\n".join(md))
    return llm_input

def write_analysis_skeleton(extracted_dir):
    """用真实数据生成中文分析骨架。不覆盖已有分析，不含 pending analysis，不含英文。"""
    out_path = os.path.join(extracted_dir, "viral_analysis.md")
    if os.path.exists(out_path):
        print("  [跳过] viral_analysis.md 已存在，不覆盖")
        return

    meta_path = os.path.join(extracted_dir, "metadata.json")
    if not os.path.exists(meta_path): return
    with open(meta_path, "r", encoding="utf-8") as f: meta = json.load(f)

    stats = meta.get("statistics", {})
    author = meta.get("author", {})
    music = meta.get("music", {}); import re; _mt = music.get("title","?"); _m = re.search(r"歌曲：(.+?)[）)]", _mt); _bgm_label = _m.group(1) if _m else (_mt if len(_mt) < 30 else _mt[:27]+"...")
    desc = meta.get("description", "")
    tags_list = [h.get("name","") for h in meta.get("hashtags",[])]
    tags_str = " ".join(["#" + t.lstrip("#＃") for t in tags_list]) if tags_list else "(无)"

    digg = max(stats.get("digg_count", 0), 1)
    share = stats.get("share_count", 0)
    collect = stats.get("collect_count", 0)
    comment = stats.get("comment_count", 0)
    sr = share / digg * 100
    cr = collect / digg * 100
    cmr = comment / digg * 100
    star = " \u2b50" if digg >= 10000 else ""

    h = [
        f"# 抖音爆款分析报告{star}", "",
        f"> 视频ID: {meta.get('video_id','')} | {meta.get('extracted_at','')[:10]}",
        f"> 类型: {meta.get('content_type','')} | 作者: {author.get('nickname','')}",
        "", "---", "",
        "## 基础数据", "",
        "| 指标 | 数值 |", "|---|---|",
        f"| 点赞 | {digg:,} |",
        f"| 评论 | {comment:,} |",
        f"| 分享 | {share:,} |",
        f"| 收藏 | {collect:,} |",
        f"| 评论/点赞比 | {cmr:.1f}% |",
        f"| 分享/点赞比 | {sr:.1f}% |",
        f"| 收藏/点赞比 | {cr:.1f}% |",
        f"| 标签 | {tags_str} |",
        f"| BGM | {_bgm_label} |",
        "", "---", "",
        ""## 1. 前3秒钩子", ""
        "\u270e 待补充：停滑策略与钩子类型", ""
        "---", ""
        "## 2. 内容结构", ""
        "\u270e 待补充", ""
        "---", ""
        "## 3. 情绪与痛点", ""
        "\u270e 待补充", ""
        "---", ""
        "## 4. 拍摄/剪辑手法", ""
        "\u270e 待补充", ""
        "---", ""
        "## 5. 行动引导（CTA）", ""
        "\u270e 待补充", ""
        "---", ""
        "## 6. 出版社复用建议", ""
        "\u270e 待补充",
    ]
    
    with open(out_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(h))
    print(f"  [生成] viral_analysis.md (* 标记处待手动补充)")

def show_materials(extracted_dir):
    """管线收尾：自动打印元数据摘要并打开关键帧拼贴图。"""
    meta_path = os.path.join(extracted_dir, "metadata.json")
    mosaic = os.path.join(extracted_dir, "keyframes", "_mosaic.jpg")
    llm_md = os.path.join(extracted_dir, "llm_input.md")
    analysis_md = os.path.join(extracted_dir, "viral_analysis.md")

    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f: meta = json.load(f)
        s = meta.get("statistics", {})
        a = meta.get("author", {})
        m = meta.get("music", {})
        d = meta.get("description", "")[:60]
        t = " ".join(["#" + h.get("name","") for h in meta.get("hashtags",[])])
        print("\n" + "=" * 50)
        print(" 素材已就绪，开始撰写分析吧")
        print("=" * 50)
        print(f"  视频ID : {meta.get('video_id','?')}")
        print(f"  类型   : {meta.get('content_type','?')}")
        print(f"  作者   : {a.get('nickname','?')}")
        print(f"  文案   : {d}{'...' if len(d)==60 else ''}")
        print(f"  标签   : {t if t else '(无)'}")
        print(f"  BGM    : {m.get('title','?')}")
        print(f"  点赞/分享/收藏/评论: {s.get('digg_count',0)} / {s.get('share_count',0)} / {s.get('collect_count',0)} / {s.get('comment_count',0)}")
        print("-" * 50)
    else:
        print("[!] metadata.json 未找到")

    if os.path.exists(mosaic):
        webbrowser.open(mosaic)
        print(f"  拼贴图 : 已打开")
    else:
        print(f"  [!] 拼贴图未找到")

    print(f"  LLM输入: {llm_md}")
    print(f"  综合分析: {os.path.join(extracted_dir, "_analysis_input.md")}")
    print(f"  分析文件: {analysis_md}" + (" (已有)" if os.path.exists(analysis_md) else " (待撰写)"))
    print("=" * 50)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    target = sys.argv[1]
    if target.endswith(".json"):
        extracted_dir = os.path.dirname(os.path.abspath(target))
    else:
        js_cmd = ["node", "extract_single.js", target]
        if HEADLESS: js_cmd.append("--headless")
        if "--no-video" in sys.argv: js_cmd.append("--no-video")
        if not run_step(js_cmd, "Step 1/3: 提取视频"): sys.exit(1)
        extracted_base = os.path.join(WORKDIR, "extracted")
        dirs = sorted([
            d for d in os.listdir(extracted_base)
            if os.path.isdir(os.path.join(extracted_base, d))
        ], key=lambda x: os.path.getmtime(os.path.join(extracted_base, x)), reverse=True)
        extracted_dir = os.path.join(extracted_base, dirs[0]) if dirs else None

    if extracted_dir:
        if not run_step(["python", "extract_keyframes.py", extracted_dir], "Step 2/3: 关键帧"): sys.exit(1)
        run_step(["python", "describe_frames.py", extracted_dir], "Step 3/3: 关键帧描述 (豆包 Vision)")
        print("\n" + "="*60 + "\n组装 LLM 输入\n" + "="*60)
        result = build_llm_input(extracted_dir)
        if result:
            print(f"\n完成! 输出: {extracted_dir}\n-> llm_input.json + llm_input.md")
            # 分析由 Codex LLM 撰写，管线不自动生成
            show_materials(extracted_dir)
            # 写入飞书（如果配置了 BASE_TOKEN）
            import os as _os
            _base_token = _os.environ.get('FEISHU_BASE_TOKEN', '')
            if _base_token:
                print('\n' + '='*60 + '\n写入飞书多维表格\n' + '='*60)
                run_step(['python', 'write_to_feishu.py', extracted_dir, '--base-token', _base_token, '--skip-if-exists'], 'Step 4/4: 写入飞书')

