"""
多厂商 LLM 爆款分析 — 支持 DeepSeek / OpenAI / 自定义 OpenAI 兼容 API
用法: python llm_analyze.py <extracted_dir> [--provider deepseek|openai|custom] [--api-key KEY] [--model MODEL] [--base-url URL]
所有参数均可通过 .env 文件或环境变量配置
"""
import sys, os, json, re
from datetime import datetime

WORKDIR = os.path.dirname(os.path.abspath(__file__))

def load_env():
    env_path = os.path.join(WORKDIR, ".env")
    if not os.path.exists(env_path):
        return {}
    config = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                config[key.strip()] = val.strip()
    return config

ENV = load_env()


def get_llm_config(args):
    """优先级: CLI 参数 > .env > 环境变量 > 默认值"""
    provider = args.get("provider") or ENV.get("LLM_PROVIDER") or os.environ.get("LLM_PROVIDER", "deepseek")
    api_key = args.get("api_key") or ENV.get("LLM_API_KEY") or os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY", "")
    model = args.get("model") or ENV.get("LLM_MODEL") or os.environ.get("LLM_MODEL", "deepseek-chat")
    base_url = args.get("base_url") or ENV.get("LLM_BASE_URL") or os.environ.get("LLM_BASE_URL", "")

    # 自动补全已知厂商的默认 base_url
    if not base_url:
        defaults = {
            "deepseek": "https://api.deepseek.com/chat/completions",
            "openai": "https://api.openai.com/v1/chat/completions",
        }
        base_url = defaults.get(provider, "")

    return {
        "provider": provider,
        "api_key": api_key,
        "model": model,
        "base_url": base_url,
    }


def load_prompt():
    prompt_path = os.path.join(WORKDIR, "viral_analysis_prompt.txt")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    return """你是一个短视频爆款分析师，专精于抖音平台的内容拆解与策略复盘。
请根据提供的素材进行6维度深度分析，输出 Markdown 格式报告。"""


def build_user_message(extracted_dir):
    parts = []
    meta_path = os.path.join(extracted_dir, "metadata.json")
    desc_path = os.path.join(extracted_dir, "keyframes", "frame_descriptions.md")

    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8", errors="replace") as f:
            meta = json.load(f)
        s = meta.get("statistics", {})
        a = meta.get("author", {})
        m = meta.get("music", {})
        tags = [h.get("name", "") for h in meta.get("hashtags", [])]
        parts.extend([
            "# 视频元数据",
            f"视频ID: {meta.get('video_id', '')}",
            f"类型: {meta.get('content_type', '')}",
            f"标题: {meta.get('title', '')}",
            f"文案: {meta.get('description', '')}",
            f"作者: {a.get('nickname', '')} | 签名: {a.get('signature', '')}",
            f"BGM: {m.get('title', '')}",
            f"标签: {' '.join(['#' + t for t in tags])}",
            "",
            "## 互动数据",
            f"点赞: {s.get('digg_count', 0)}",
            f"评论: {s.get('comment_count', 0)}",
            f"分享: {s.get('share_count', 0)}",
            f"收藏: {s.get('collect_count', 0)}",
        ])

    if os.path.exists(desc_path):
        with open(desc_path, "r", encoding="utf-8-sig") as f:
            desc_text = f.read()
        parts.extend(["", "---", "", "# 关键帧画面描述", desc_text])

    return "\n".join(parts)


def call_llm(system_prompt, user_message, cfg):
    """调用 OpenAI 兼容 API（适用于 DeepSeek / OpenAI / 自定义）"""
    import urllib.request, urllib.error

    api_key = cfg["api_key"]
    base_url = cfg["base_url"] or "https://api.deepseek.com/chat/completions"

    if not api_key:
        raise RuntimeError(
            f"未配置 LLM API Key。请在 .env 中设置 LLM_API_KEY，"
            f"或在前端设置面板中填写。\n"
            f"当前提供商: {cfg['provider']}"
        )

    payload = json.dumps({
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7,
        "max_tokens": 8192,
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(base_url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if e.code == 401:
            raise RuntimeError(f"API Key 无效或已过期 ({cfg['provider']})。请检查 .env 中的 LLM_API_KEY。")
        raise RuntimeError(f"LLM API 错误 ({e.code}): {body[:300]}")
    except Exception as e:
        raise RuntimeError(f"LLM API 调用失败: {e}")


def write_skeleton_header(extracted_dir, meta):
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
        "---", "",
        "## 基础数据", "",
        "| 指标 | 数值 |", "|---|---|",
        f"| 点赞 | {digg:,} |",
        f"| 评论 | {comment:,} |",
        f"| 分享 | {share:,} |",
        f"| 收藏 | {collect:,} |",
        f"| 评论/点赞比 | {comment/digg*100:.1f}% |",
        f"| 分享/点赞比 | {share/digg*100:.1f}% |",
        f"| 收藏/点赞比 | {collect/digg*100:.1f}% |",
        "", "---", "",
    ]
    with open(out_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(header))
    return out_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="多厂商 LLM 自动撰写爆款分析")
    parser.add_argument("extracted_dir", help="提取目录路径")
    parser.add_argument("--provider", default=None, help="LLM 提供商 (deepseek/openai/custom)")
    parser.add_argument("--api-key", default=None, help="API Key")
    parser.add_argument("--model", default=None, help="模型名称")
    parser.add_argument("--base-url", default=None, help="API Base URL（OpenAI 兼容格式）")
    args = parser.parse_args()

    cfg = get_llm_config({
        "provider": args.provider,
        "api_key": args.api_key,
        "model": args.model,
        "base_url": args.base_url,
    })

    print(f"  提供商: {cfg['provider']} | 模型: {cfg['model']}")
    print(f"  Base URL: {cfg['base_url']}")

    meta_path = os.path.join(args.extracted_dir, "metadata.json")
    if not os.path.exists(meta_path):
        print(f"[ERROR] metadata.json not found: {meta_path}")
        sys.exit(1)

    with open(meta_path, "r", encoding="utf-8", errors="replace") as f:
        meta = json.load(f)

    out_path = write_skeleton_header(args.extracted_dir, meta)
    print(f"  骨架: {out_path}")

    system_prompt = load_prompt()
    user_message = build_user_message(args.extracted_dir)
    print(f"  上下文: {len(user_message)} 字符")

    print("  正在分析...")
    analysis = call_llm(system_prompt, user_message, cfg)

    with open(out_path, "a", encoding="utf-8-sig") as f:
        f.write(analysis)
    print(f"  [OK] 分析完成 ({len(analysis)} chars)")

    meta["analysis_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(meta_path, "w", encoding="utf-8", errors="replace") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
