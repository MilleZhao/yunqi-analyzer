"""
DeepSeek 爆款分析 — 读取元数据+关键帧描述，自动撰写6维度分析报告
用法: python deepseek_analyze.py <extracted_dir> [--model deepseek-chat]
依赖: DEEPSEEK_API_KEY 环境变量
"""
import sys, os, json, re
from datetime import datetime

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"


def load_prompt():
    """加载分析提示词模板"""
    prompt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "viral_analysis_prompt.txt")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    # fallback: 内置简化版
    return """你是一个短视频爆款分析师，专精于抖音平台的内容拆解与策略复盘。
请根据提供的素材进行6维度深度分析，输出 Markdown 格式报告。"""


def build_user_message(extracted_dir):
    """组装发送给 DeepSeek 的完整上下文"""
    meta_path = os.path.join(extracted_dir, "metadata.json")
    desc_path = os.path.join(extracted_dir, "keyframes", "frame_descriptions.md")

    parts = []

    # 元数据
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8", errors="replace") as f:
            meta = json.load(f)

        s = meta.get("statistics", {})
        a = meta.get("author", {})
        m = meta.get("music", {})
        tags = [h.get("name", "") for h in meta.get("hashtags", [])]

        parts.append("# 视频元数据")
        parts.append(f"视频ID: {meta.get('video_id', '')}")
        parts.append(f"类型: {meta.get('content_type', '')}")
        parts.append(f"标题: {meta.get('title', '')}")
        parts.append(f"文案: {meta.get('description', '')}")
        parts.append(f"作者: {a.get('nickname', '')} | 签名: {a.get('signature', '')}")
        parts.append(f"BGM: {m.get('title', '')}")
        parts.append(f"标签: {' '.join(['#' + t for t in tags])}")
        parts.append("")
        parts.append("## 互动数据")
        parts.append(f"点赞: {s.get('digg_count', 0)}")
        parts.append(f"评论: {s.get('comment_count', 0)}")
        parts.append(f"分享: {s.get('share_count', 0)}")
        parts.append(f"收藏: {s.get('collect_count', 0)}")

    # 关键帧描述
    if os.path.exists(desc_path):
        with open(desc_path, "r", encoding="utf-8-sig") as f:
            desc_text = f.read()
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append("# 关键帧画面描述")
        parts.append(desc_text)

    return "\n".join(parts)


def call_deepseek(system_prompt, user_message, model=DEFAULT_MODEL):
    """调用 DeepSeek Chat API"""
    import urllib.request, urllib.error

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(DEEPSEEK_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {DEEPSEEK_KEY}")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DeepSeek API error {e.code}: {body[:300]}")
    except Exception as e:
        raise RuntimeError(f"DeepSeek API call failed: {e}")


def write_skeleton_header(extracted_dir, meta):
    """先写入骨架头部（含基础数据表），DeepSeek 返回后追加内容"""
    out_path = os.path.join(extracted_dir, "viral_analysis.md")
    stats = meta.get("statistics", {})
    author = meta.get("author", {})
    music = meta.get("music", {})
    tags_list = [h.get("name", "") for h in meta.get("hashtags", [])]
    tags_str = " ".join(["#" + t.lstrip("#＃") for t in tags_list]) if tags_list else "(无)"
    bgm = music.get("title", "?")
    bgm_short = bgm if len(bgm) < 30 else bgm[:27] + "..."

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    digg = max(stats.get("digg_count", 0), 1)
    share = stats.get("share_count", 0) or 0
    collect = stats.get("collect_count", 0) or 0
    comment = stats.get("comment_count", 0) or 0

    header = [
        "# 抖音爆款分析报告",
        "",
        f"> 视频ID: {meta.get('video_id', '')} | 分析时间: {now}",
        f"> 类型: {meta.get('content_type', '')} | 作者: {author.get('nickname', '')}",
        f"> 标签: {tags_str} | BGM: {bgm_short}",
        "",
        "---",
        "",
        "## 基础数据",
        "",
        "| 指标 | 数值 |",
        "|---|---|",
        f"| 点赞 | {digg:,} |",
        f"| 评论 | {comment:,} |",
        f"| 分享 | {share:,} |",
        f"| 收藏 | {collect:,} |",
        f"| 评论/点赞比 | {comment/digg*100:.1f}% |",
        f"| 分享/点赞比 | {share/digg*100:.1f}% |",
        f"| 收藏/点赞比 | {collect/digg*100:.1f}% |",
        "",
        "---",
        "",
    ]
    with open(out_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(header))
    return out_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="DeepSeek 自动撰写爆款分析")
    parser.add_argument("extracted_dir", help="提取目录路径")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="DeepSeek 模型 (默认 deepseek-chat)")
    args = parser.parse_args()

    if not DEEPSEEK_KEY:
        print("[ERROR] DEEPSEEK_API_KEY not set")
        sys.exit(1)

    meta_path = os.path.join(args.extracted_dir, "metadata.json")
    if not os.path.exists(meta_path):
        print(f"[ERROR] metadata.json not found: {meta_path}")
        sys.exit(1)

    with open(meta_path, "r", encoding="utf-8", errors="replace") as f:
        meta = json.load(f)

    # 1. 写骨架
    out_path = write_skeleton_header(args.extracted_dir, meta)
    print(f"  骨架: {out_path}")

    # 2. 组装上下文
    system_prompt = load_prompt()
    user_message = build_user_message(args.extracted_dir)
    print(f"  上下文: {len(user_message)} 字符")

    # 3. 调用 DeepSeek
    print(f"  模型: {args.model}")
    print("  正在分析...")
    analysis = call_deepseek(system_prompt, user_message, args.model)

    # 4. 追加到文件
    with open(out_path, "a", encoding="utf-8-sig") as f:
        f.write(analysis)
    print(f"  [OK] 分析完成 ({len(analysis)} chars)")
    print(f"  输出: {out_path}")

    # 5. 更新 metadata 记录分析时间
    meta["analysis_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(meta_path, "w", encoding="utf-8", errors="replace") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
