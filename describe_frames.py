"""
关键帧描述器 — 用火山引擎豆包 Vision API 将关键帧转为结构化文字描述
用法: python describe_frames.py <extracted_dir> [--model <endpoint_id>]
输出: keyframes/frame_descriptions.md + _analysis_input.md

核心价值: Codex 分析时不再需要 view_image 看图片，只读文字描述即可，
          省掉 95%+ 的上下文 token 消耗，彻底解决 context compaction 问题。

火山引擎配置:
  base_url: https://ark.cn-beijing.volces.com/api/v3
  model: 需在 Ark 控制台创建推理接入点，获取 endpoint ID（ep-xxxx 格式）
"""
import sys, os, json, base64, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

# ========== 加载 .env 配置 ==========
def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
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

_ENV = _load_env()

# ========== 火山引擎 Ark 配置 ==========
ARK_BASE_URL = _ENV.get("VISION_BASE_URL") or os.environ.get("VISION_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
ARK_API_KEY = _ENV.get("VISION_API_KEY") or os.environ.get("VISION_API_KEY", "")
DEFAULT_MODEL = _ENV.get("VISION_MODEL") or os.environ.get("VISION_MODEL", "doubao-seed-1-8-251228")  # 默认模型名

# Tesseract OCR 路径 — 自动检测
import shutil as _shutil
def _find_tesseract():
    """Auto-detect tesseract executable"""
    if sys.platform == "win32":
        for c in ["C:\\Program Files\\Tesseract-OCR\\tesseract.exe", "C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe"]:
            if os.path.exists(c): return c
    found = _shutil.which("tesseract")
    if found: return found
    return "tesseract"
TESSERACT_PATH = _find_tesseract()

SYSTEM_PROMPT = """你是一个抖音短视频内容分析师。你正在分析一个视频/图文的关键帧截图。
请用简洁的 2-3 句中文描述这个画面，重点关注：
1. 画面上有什么文字（逐字读出，这是最重要的信息）
2. 视觉元素：人物、产品、图表、场景
3. 色彩风格和排版特点（大字报？清新文艺？数据图表？）
4. 这帧在内容中的叙事功能（封面钩子？论证支撑？结尾行动号召？）

只返回纯文本描述，不要加格式、序号或前缀。"""


def describe_image(client, image_path, model):
    """调用火山引擎 Responses API (doubao-seed) 描述单张图片"""
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    ext = os.path.splitext(image_path)[1].lower().replace(".", "")
    mime = f"image/{ext}" if ext in ("jpg","jpeg","png","webp","gif") else "image/jpeg"

    response = client.responses.create(
        model=model,
        input=[{
            "role": "user",
            "content": [
                {"type": "input_image", "image_url": f"data:{mime};base64,{b64}"},
                {"type": "input_text", "text": "请描述这张关键帧的画面内容（2-3句中文）"},
            ]
        }]
    )
    return response.output_text.strip()

def ocr_image(image_path):
    """用 Tesseract OCR 提取图片中的文字（API 不可用时的本地兜底）"""
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
        from PIL import Image
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        return text.strip()[:200] if text.strip() else None
    except Exception as e:
        return None


def describe_frames(extracted_dir, model=DEFAULT_MODEL, max_workers=3, use_ocr_fallback=True):
    keyframes_dir = os.path.join(extracted_dir, "keyframes")
    if not os.path.isdir(keyframes_dir):
        print(f"  关键帧目录不存在: {keyframes_dir}")
        return None

    frames = sorted([
        f for f in os.listdir(keyframes_dir)
        if f.endswith(".jpg") and f.startswith("frame_")
    ])
    if not frames:
        print("  无关键帧需要描述")
        return None

    print(f"\n{'='*50}")
    print(f"  关键帧描述")
    print(f"  Endpoint: {model} | 帧数: {len(frames)} | 并发: {max_workers}")
    print(f"{'='*50}")

    client = OpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL, timeout=30)

    # 逐帧描述，并发处理
    descriptions = {}
    t0 = time.time()
    frame_paths = [(f, os.path.join(keyframes_dir, f)) for f in frames]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(describe_image, client, fp, model): fn
            for fn, fp in frame_paths
        }
        completed = 0
        for future in as_completed(future_map):
            fn = future_map[future]
            try:
                desc = future.result()
                descriptions[fn] = desc
                completed += 1
                preview = desc[:60] + ('...' if len(desc) > 60 else '')
                print(f"  [{completed}/{len(frames)}] {fn}: {preview}")
            except Exception as e:
                err_msg = str(e)[:80]
                print(f"  [{completed+1}/{len(frames)}] {fn}: API失败 - {err_msg}")
                # OCR 兜底
                if use_ocr_fallback:
                    ocr_text = ocr_image(os.path.join(keyframes_dir, fn))
                    if ocr_text:
                        descriptions[fn] = f"[OCR提取] {ocr_text}"
                        completed += 1
                        print(f"     -> OCR兜底: {ocr_text[:60]}...")
                    else:
                        descriptions[fn] = "(描述失败，无可用文字)"
                        completed += 1
                else:
                    descriptions[fn] = "(描述失败)"

    elapsed = time.time() - t0
    print(f"  耗时: {elapsed:.1f}s ({elapsed/len(frames):.1f}s/帧)")

    # 写入 frame_descriptions.md
    desc_path = os.path.join(keyframes_dir, "frame_descriptions.md")
    lines = ["# 关键帧文字描述", "", f"自动生成 | 模型: {model} | {len(frames)} 帧", ""]
    for fn in frames:
        desc = descriptions.get(fn, "(无)")
        lines.append(f"## {fn}")
        lines.append(f"{desc}")
        lines.append("")
    with open(desc_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))
    print(f"  输出: {desc_path}")

    # 生成综合分析输入文件 (_analysis_input.md)
    meta_path = os.path.join(extracted_dir, "metadata.json")
    analysis_path = os.path.join(extracted_dir, "_analysis_input.md")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8", errors="replace") as f:
            meta = json.load(f)
        s = meta.get("statistics", {})
        a = meta.get("author", {})
        m = meta.get("music", {})
        h = meta.get("hashtags", [])
        digg = max(s.get("digg_count", 0), 1)
        ai_lines = [
            "# 综合分析输入",
            "",
            "## 基础数据",
            f"- 视频ID: {meta.get('video_id', '?')}",
            f"- 类型: {meta.get('content_type', '?')}",
            f"- 标题: {meta.get('title', '(无)')}",
            f"- 文案: {meta.get('description', '(无)')}",
            f"- 标签: {' '.join(['#'+t.get('name','') for t in h]) if h else '(无)'}",
            f"- 作者: {a.get('nickname', '?')} | 签名: {a.get('signature', '?')}",
            f"- BGM: {m.get('title', '?')}",
            f"- 点赞: {digg:,} | 评论: {s.get('comment_count',0):,} | 分享: {s.get('share_count',0):,} | 收藏: {s.get('collect_count',0):,}",
            f"- 评论/点赞: {s.get('comment_count',0)/digg*100:.1f}% | 分享/点赞: {s.get('share_count',0)/digg*100:.1f}% | 收藏/点赞: {s.get('collect_count',0)/digg*100:.1f}%",
            "",
            f"## 关键帧描述 ({len(frames)} 帧)",
            "",
            *(f"- **{fn}**: {descriptions.get(fn, '(无)')}" for fn in frames),
            "",
        ]
        with open(analysis_path, "w", encoding="utf-8-sig") as f:
            f.write("\n".join(ai_lines))
        print(f"  综合分析: {analysis_path}")

    return desc_path


if __name__ == "__main__":
    model = DEFAULT_MODEL
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--model" and i + 1 < len(args):
            model = args[i + 1]
            args.pop(i)  # remove --model
            args.pop(i)  # remove value
            break

    if len(args) < 1:
        print(__doc__)
        print(f"\n当前默认模型: {DEFAULT_MODEL}")
        print("提示: 在火山引擎 Ark 控制台创建推理接入点后，用 --model <endpoint_id> 指定")
        sys.exit(1)

    result = describe_frames(args[0], model=model)
    if result:
        print(f"\n  DONE: {result}")
    else:
        sys.exit(1)





