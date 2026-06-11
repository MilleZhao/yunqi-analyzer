"""写入飞书多维表格 — 将爆款分析结果自动归档到飞书 Base
用法: python write_to_feishu.py <extracted_dir> --base-token <BASE_TOKEN> [--table-id <TABLE_ID>]
依赖: lark-cli 已安装并登录
"""
import sys, os, json, subprocess, re, platform
from datetime import datetime
def strip_md(text):
    if not text:
        return ""
    text = re.sub(r'\*{1,3}([^*]+?)\*{1,3}', r'\1', text)
    text = re.sub(r'(?m)^\s*[-*+]\s+', '', text)
    text = re.sub(r'(?m)^\s*\d+[.)]\s+', '', text)
    text = re.sub(r'(?m)^#{1,6}\s*', '', text)
    text = re.sub(r'(?m)^[-*_]{3,}\s*$', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = '\n'.join(line.strip() for line in text.split('\n'))
    return text.strip()


CLI = os.path.expanduser("~/go/bin/cli.exe" if platform.system() == "Windows" else "~/go/bin/cli")

def grade_by_likes(likes):
    if likes >= 100000:   return "S-超爆"
    elif likes >= 10000:  return "A-大爆"
    elif likes >= 1000:   return "B-小爆"
    return "C-普通"

def run_lark(*args, input_data=None):
    cmd = [CLI] + [str(a) for a in args]
    if input_data:
        proc = subprocess.run(cmd, input=input_data, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    else:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    if proc.returncode != 0:
        raise RuntimeError(f"lark-cli failed: {proc.stderr[:200]}")
    return json.loads(proc.stdout) if proc.stdout and proc.stdout.strip() else {}

def ensure_table(base_token, table_name="爆款分析结果"):
    tables = run_lark("base", "+table-list", "--base-token", base_token, "--json")
    for t in tables.get("data", {}).get("tables", []):
        if t.get("name") == table_name:
            return t["id"]
    result = run_lark("base", "+table-create", "--base-token", base_token, "--name", table_name)
    return result.get("data", {}).get("table_id", "")

def extract_text_block(text, heading_patterns):
    for pat in heading_patterns:
        m = re.search(pat, text, re.DOTALL)
        if m:
            raw = m.group(1).strip()
            raw = re.sub(r"[待]\s*待补充[^\n]*", "", raw).strip()
            raw = re.sub(r"\n{3,}", "\n\n", raw)
            return raw[:500]
    return ""

def extract_summary(extracted_dir):
    """从提取目录读取元数据和分析结论"""
    meta_path = os.path.join(extracted_dir, "metadata.json")
    analysis_path = os.path.join(extracted_dir, "viral_analysis.md")

    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"metadata.json not found: {meta_path}")

    with open(meta_path, "r", encoding="utf-8", errors="replace") as f:
        meta = json.load(f)

    s = meta.get("statistics", {})
    a = meta.get("author", {})
    music = meta.get("music", {})
    digg = max(s.get("digg_count", 0), 1) if s else 1
    share = (s.get("share_count", 0) or 0) if s else 0
    collect = (s.get("collect_count", 0) or 0) if s else 0
    comment = (s.get("comment_count", 0) or 0) if s else 0

    # 爆款等级：纯按点赞数
    grade = grade_by_likes(digg)

    # 读取分析报告
    analysis_text = ""
    if os.path.exists(analysis_path):
        with open(analysis_path, "r", encoding="utf-8-sig") as f:
            analysis_text = f.read()

    # ---------- 提取各维度 ----------
    core_insight = ""
    hook_type = ""
    hook_3s = ""          # 前3秒钩子
    content_struct = ""   # 内容结构
    emotion_tag = ""      # 情绪标签
    target_audience = ""  # 目标受众
    shoot_style = ""      # 拍摄手法
    cta_type = ""         # CTA类型
    reuse_tip = ""        # 可复用建议

    if analysis_text:
        # ---- core insight ----
        for pat in [
            r"[-*]\s*\*{0,2}\u6838\u5fc3\u9a71\u52a8\u529b\*{0,2}\s*[:\uff1a]\s*(.+?)(?:\n[-*]|\n\n|\n+#|\Z)",
            r"###?\s*(?:\u6838\u5fc3\u6d1e\u5bdf|\u6838\u5fc3\u9a71\u52a8\u529b|\u7206\u6b3e\u539f\u56e0\u5f52\u56e0).*?\n+(.+?)(?:\n\n---|\n\n##|\n+#)",
            r"##\s*5\.\s*\u6838\u5fc3\u6d1e\u5bdf.*?\n+(.+?)(?:\n+#)",
        ]:
            rm = re.search(pat, analysis_text, re.DOTALL)
            if rm:
                raw = rm.group(1).strip()
                core_insight = re.sub(r"\u270e\s*\u5f85\u8865\u5145[^\n]*", "", raw).strip()[:500]
                break

        # ---- hook type ----
        if "\u8ba4\u77e5\u51b2\u7a81" in analysis_text:       hook_type = "\u8ba4\u77e5\u51b2\u7a81"
        elif "\u60c5\u7eea\u5171\u9e23" in analysis_text or "\u60c5\u7eea\u94a9\u5b50" in analysis_text: hook_type = "\u60c5\u7eea\u5171\u9e23"
        elif "\u5229\u76ca" in analysis_text:         hook_type = "\u5229\u76ca\u8bf1\u5bfc"
        elif "\u89c6\u89c9\u51b2\u51fb" in analysis_text or "\u89c6\u89c9\u94a9\u5b50" in analysis_text: hook_type = "\u89c6\u89c9\u51b2\u51fb"
        elif "\u4fe1\u606f\u5dee" in analysis_text:       hook_type = "\u4fe1\u606f\u5dee"
        elif "\u597d\u5947" in analysis_text:         hook_type = "\u597d\u5947"

        # ---- hook 3s ----
        hook_3s = extract_text_block(analysis_text, [
            r"[-*]\s*\*{0,2}\u94a9\u5b50\u7b56\u7565\*{0,2}\s*[:\uff1a]\s*(.+?)(?:\n[-*]|\n##|\Z)",
            r"##\s*1\.\s*\u524d3\u79d2\u94a9\u5b50.*?\n+(.+?)(?:\n##|\Z)",

            r"[-*]\s*\*{0,2}\u5c01\u9762\s*/?\s*\u9996\u5e27\*{0,2}\s*[:\uff1a]\s*(.+?)(?:\n[-*]|\n\n|\Z)",
            r"###?\s*(?:\u5c01\u9762|\u9996\u5e27|\u524d3\u79d2|\u524d3\u79d2\u94a9\u5b50).*?\n+(.+?)(?:\n+#)",
            r"##\s*1\.\s*\u7206\u6b3e\u5143\u7d20\u62c6\u89e3.*?\n###?\s*\u5c01\u9762.*?\n+(.+?)(?:\n+#)",
        ]) or extract_text_block(analysis_text, [
            r"##\s*1\.\s*\u524d3\u79d2.*?\n+(.+?)(?:\n+#)",
        ])

        # ---- content structure ----
        content_struct = extract_text_block(analysis_text, [
            r"##\s*2\.\s*\u5185\u5bb9\u7ed3\u6784.*?\n+(.+?)(?:\n##|\Z)",

            r"[-*]\s*\*{0,2}\u5267\u60c5\u7ed3\u6784\*{0,2}\s*[:\uff1a]\s*(.+?)(?:\n[-*]|\n\n|\Z)",
            r"###?\s*(?:\u5267\u60c5\u7ed3\u6784|\u5185\u5bb9\u7ed3\u6784).*?\n+(.+?)(?:\n+#)",
            r"##\s*2\.\s*\u5185\u5bb9\u7ed3\u6784.*?\n+(.+?)(?:\n+#)",
        ])

        # ---- emotion tag ----
        emotion_tag = extract_text_block(analysis_text, [
            r"[-*]\s*\*{0,2}\u89e6\u53d1\u60c5\u7eea\*{0,2}\s*[:\uff1a]\s*(.+?)(?:\n[-*]|\n##|\Z)",
            r"##\s*[34]\.\s*\u60c5\u7eea\u4e0e\u75db\u70b9.*?\n+(.+?)(?:\n##|\Z)",

            r"[-*]\s*\*{0,2}(?:\u5174\u8da3\u6807\u7b7e|\u60c5\u7eea\u6807\u7b7e)\*{0,2}\s*[:\uff1a]\s*(.+?)(?:\n[-*]|\n\n|\Z)",
            r"###?\s*(?:\u60c5\u7eea\u6807\u7b7e|\u60c5\u7eea\u4e0e\u75db\u70b9|\u60c5\u7eea).*?\n+(.+?)(?:\n+#)",
            r"##\s*[34]\.\s*\u60c5\u7eea\u4e0e\u75db\u70b9.*?\n+(.+?)(?:\n+#)",
        ])
        if not emotion_tag and core_insight:
            first_sent = re.split(r"[\u3002\uff1b\n]", core_insight)[0]
            emotion_tag = first_sent[:100]

        # ---- target audience ----
        target_audience = extract_text_block(analysis_text, [
            r"[-*]\s*\*{0,2}(?:\u4eba\u7fa4\u753b\u50cf|\u76ee\u6807\u53d7\u4f17)\*{0,2}\s*[:\uff1a]\s*(.+?)(?:\n[-*]|\n\n|\Z)",
            r"##\s*[23]\.\s*\u76ee\u6807\u53d7\u4f17.*?\n+(.+?)(?:\n+#)",
            r"###?\s*\u76ee\u6807\u53d7\u4f17.*?\n+(.+?)(?:\n+#)",
        ])

        # ---- shoot style (fallback to content_struct) ----
        shoot_style = extract_text_block(analysis_text, [
            r"##\s*[46]\.\s*\u62cd\u6444.*?\n+(.+?)(?:\n##|\Z)",

            r"##\s*[46]\.\s*\u62cd[\u6444\u526a].*?\n+(.+?)(?:\n+#)",
            r"###?\s*\u62cd[\u6444\u526a].*?\n+(.+?)(?:\n+#)",
        ])
        # no fallback — keep empty if not found

        # ---- CTA type ----
        cta_block = extract_text_block(analysis_text, [
            r"[-*]\s*\*{0,2}CTA\u7c7b\u578b\*{0,2}\s*[:\uff1a]\s*(.+?)(?:\n[-*]|\n##|\Z)",
            r"##\s*[57]\.\s*\u884c\u52a8\u5f15\u5bfc.*?\n+(.+?)(?:\n##|\Z)",

            r"[-*]\s*\*{0,2}(?:CTA\u7c7b\u578b|CTA|\u884c\u52a8\u5f15\u5bfc)\*{0,2}\s*[:\uff1a]\s*(.+?)(?:\n[-*]|\n##|\n\n|\Z)",
            r"##\s*(?:CTA\u5206\u6790|CTA).*?\n[-*].*?\n+(.+?)(?:\n##|\Z)",
            r"##\s*[57]\.\s*(?:\u884c\u52a8|CTA).*?\n+(.+?)(?:\n+#)",
            r"###?\s*(?:CTA|\u884c\u52a8\u5f15\u5bfc).*?\n+(.+?)(?:\n+#)",
        ])
        if cta_block:
            if "\u5546\u54c1" in cta_block or "\u94fe\u63a5" in cta_block: cta_type = "\u5546\u54c1\u5f15\u5bfc"
            elif "\u5173\u6ce8" in cta_block:                       cta_type = "\u5173\u6ce8\u5f15\u5bfc"
            elif "\u8bc4\u8bba" in cta_block:                       cta_type = "\u8bc4\u8bba\u533a\u5f15\u5bfc"
            elif "\u4e3b\u9875" in cta_block:                       cta_type = "\u4e3b\u9875\u5f15\u5bfc"
            elif "\u60c5\u7eea" in cta_block or "\u6536\u5c3e" in cta_block: cta_type = "\u60c5\u7eea\u6536\u5c3e"
            else:                                           cta_type = "\u65e0"

        # ---- reuse tips ----
        reuse_tip = extract_text_block(analysis_text, [
            r"[-*]\s*\*{0,2}\u53ef\u76f4\u63a5\u590d\u7528\*{0,2}\s*[:\uff1a]\s*(.+?)(?:\n[-*]|\n##|\Z)",
            r"##\s*[68]\.\s*\u51fa\u7248\u793e\u590d\u7528.*?\n+(.+?)(?:\n##|\Z)",

            r"[-*]\s*\*{0,2}(?:\u53ef\u76f4\u63a5\u590d\u7528|\u53ef\u590d\u7528\u5efa\u8bae)\*{0,2}\s*[:\uff1a]\s*(.+?)(?:\n[-*]|\n##|\Z)",
            r"##\s*[468]\.\s*(?:\u53ef\u590d\u7528|\u51fa\u7248\u793e\u590d\u7528).*?\n+(.+?)(?:\n+#)",
            r"###?\s*\u53ef\u76f4\u63a5\u590d\u7528.*?\n+(.+?)(?:\n+#)",
        ])
    # BGM
    bgm_title = ""
    if music:
        _mt = music.get("title", "")
        _mm = re.search(r"歌曲：(.+?)[）)]", _mt)
        bgm_title = _mm.group(1) if _mm else (_mt if len(_mt) < 50 else _mt[:47] + "...")

    # 话题标签
    tags_list = [h.get("name", "") for h in meta.get("hashtags", [])]
    tags_str = " ".join(["#" + t.lstrip("#＃") for t in tags_list]) if tags_list else ""

    video_id = meta.get("video_id", "")
    video_url = f"https://www.douyin.com/video/{video_id}" if video_id else ""
    analysis_time = meta.get("analysis_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # 分析报告正文（而非文件路径）
    report_body = analysis_text[:8000] if analysis_text else ""
    report_body = re.sub(r"\u270e\s*待补充[^\n]*\n?", "", report_body)

    return {
        "video_id": str(video_id),
        "fields": {
            "视频ID": str(video_id) if video_id else "",
            "视频链接": video_url if video_url else "",
            "标题": (meta.get("title", "") or "")[:200],
            "作者": a.get("nickname", "") if a else "",
            "类型": "视频" if meta.get("content_type") == "video" else "图文",
            "点赞数": digg,
            "评论数": comment,
            "分享数": share,
            "收藏数": collect,
            "爆款等级": grade,
            "前3秒钩子": strip_md(hook_3s),
            "内容结构": strip_md(content_struct),
            "情绪标签": strip_md(emotion_tag),
            "核心洞察": strip_md(core_insight),
            "目标受众": strip_md(target_audience),
            "钩子类型": hook_type,
            "拍摄手法": strip_md(shoot_style),
            "CTA类型": cta_type,
            "可复用建议": strip_md(reuse_tip),
            "BGM": bgm_title,
            "话题标签": tags_str,
            "分析时间": analysis_time,

        }
    }


def write_record(base_token, table_id, record_data):
    """写入一条记录到飞书多维表格"""
    fields = record_data["fields"]
    payload = json.dumps(fields, ensure_ascii=False)
    result = run_lark(
        "base", "+record-upsert",
        "--base-token", base_token,
        "--table-id", table_id,
        "--json", payload,
    )
    record_id = result.get("data", {}).get("record", {}).get("record_id_list", [""])[0] or ""
    return record_id


def upload_attachment(base_token, table_id, record_id, field_id, file_path):
    """上传文件到记录的附件字段"""
    if not os.path.exists(file_path):
        print(f"  (附件文件不存在: {file_path})")
        return False
    rel_path = os.path.relpath(file_path).replace(os.sep, "/")
    try:
        result = run_lark(
            "base", "+record-upload-attachment",
            "--base-token", base_token,
            "--table-id", table_id,
            "--record-id", record_id,
            "--field-id", field_id,
            "--file", rel_path,
        )
        return result.get("ok", False)
    except RuntimeError as e:
        print(f"  (附件上传失败: {str(e)[:120]})")
        return False


def check_existing(base_token, table_id, video_id):
    """检查是否已有同名记录"""
    result = run_lark(
        "base", "+record-search",
        "--base-token", base_token,
        "--table-id", table_id,
        "--keyword", video_id,
        "--search-field", "视频ID",
        "--field-id", "视频ID",
        "--limit", "5",
        "--format", "json",
    )
    items = result.get("data", {}).get("items", [])
    if items:
        return items[0].get("record_id")
    return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="写入爆款分析结果到飞书多维表格")
    parser.add_argument("extracted_dir", help="提取目录路径")
    parser.add_argument("--base-token", required=True, help="飞书 Base Token")
    parser.add_argument("--table-id", help="表 ID（可选，不存在则自动创建）")
    parser.add_argument("--skip-if-exists", action="store_true", help="如果已存在同视频ID的记录则跳过")
    args = parser.parse_args()

    print(f"  读取分析数据: {args.extracted_dir}")
    record_data = extract_summary(args.extracted_dir)

    if args.table_id:
        table_id = args.table_id
    else:
        table_id = ensure_table(args.base_token)

    video_id = record_data["video_id"]
    if args.skip_if_exists:
        try:
            existing = check_existing(args.base_token, table_id, video_id)
            if existing:
                print(f"  跳过: 视频 {video_id} 已存在 (record_id={existing})")
                return
        except Exception:
            print("  (搜索跳过: 表可能无此字段)")

    record_id = write_record(args.base_token, table_id, record_data)

    # 上传分析报告附件
    analysis_file = os.path.join(args.extracted_dir, "viral_analysis.md")
    if os.path.exists(analysis_file):
        import time; time.sleep(1)  # 等记录索引生效
        ok = upload_attachment(args.base_token, table_id, record_id, "fldQwLRx8v", analysis_file)
        if ok:
            print("  [附件] 分析报告附件已上传")

    f = record_data["fields"]
    print(f"  写入成功!")
    print(f"  视频: {video_id} | {f['标题'][:30]}")
    print(f"  数据: {f['点赞数']}赞 | 等级: {f['爆款等级']}")
    print(f"  核心洞察: {f['核心洞察'][:60] if f['核心洞察'] else '(待分析)'}")


if __name__ == "__main__":
    main()

