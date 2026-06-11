"""
导出分析报告到飞书在线文档 — 通过 lark-cli 调用飞书 Doc API
用法: python export_feishu_doc.py <extracted_dir>
依赖: lark-cli 已认证（cli auth login）
"""
import sys, os, json, subprocess, platform
from write_to_feishu import extract_summary

WORKDIR = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.expanduser("~/go/bin/cli.exe" if platform.system() == "Windows" else "~/go/bin/cli")


def call_api(method, path, data=None):
    cmd = [CLI, "api", method, path]
    if data:
        cmd += ["--data", json.dumps(data, ensure_ascii=False)]
    result = subprocess.run(cmd, cwd=WORKDIR, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"lark-cli error: {result.stderr[:300]}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"lark-cli non-JSON: {result.stdout[:300]}")


def create_doc(title):
    resp = call_api("POST", "/open-apis/docx/v1/documents",
                    {"title": title})
    code = resp.get("code", -1)
    if code != 0:
        raise RuntimeError(f"Create doc failed (code={code}): {resp.get('msg', resp)}")
    return resp["data"]["document"]["document_id"]


def add_blocks(doc_id, blocks):
    resp = call_api("POST",
                    f"/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children",
                    {"children": blocks, "index": -1})
    code = resp.get("code", -1)
    if code != 0:
        raise RuntimeError(f"Add blocks failed (code={code}): {resp.get('msg', resp)}")


# ---- Block builders ----
def h1(text): return {"block_type": 3, "heading1": txt_el(text)}
def h2(text): return {"block_type": 4, "heading2": txt_el(text)}
def para(text): return {"block_type": 2, "text": txt_el(text)}

def txt_el(text):
    lines = []
    for line in text.split("\n"):
        if line.strip():
            lines.append({"text_run": {"content": line + "\n"}})
    return {"elements": lines, "style": {}}


def build_doc(fields):
    blocks = []
    title = fields.get("标题", "(无标题)")
    blocks.append(h1(f"爆款分析: {title}"))
    pass  # divider not supported at root level

    # Basic info
    info = "\n".join([
        f"视频ID: {fields.get('视频ID', '')}",
        f"作者: {fields.get('作者', '')}",
        f"类型: {fields.get('类型', '')}",
        f"点赞: {fields.get('点赞数', 0)}  评论: {fields.get('评论数', 0)}  分享: {fields.get('分享数', 0)}  收藏: {fields.get('收藏数', 0)}",
        f"爆款等级: {fields.get('爆款等级', '')}",
        f"BGM: {fields.get('BGM', '')}",
        f"话题: {fields.get('话题标签', '')}",
        f"分析时间: {fields.get('分析时间', '')}",
    ])
    blocks.append(para(info))
    pass  # divider not supported at root level

    dims = [
        ("前3秒钩子", "前3秒钩子"),
        ("内容结构", "内容结构"),
        ("目标受众", "目标受众"),
        ("核心洞察", "核心洞察"),
        ("情绪与痛点", "情绪标签"),
        ("拍摄手法", "拍摄手法"),
        ("CTA", "CTA类型"),
        ("出版社复用建议", "可复用建议"),
    ]
    for heading, key in dims:
        val = fields.get(key, "")
        if val and val.strip():
            blocks.append(h2(heading))
            blocks.append(para(val))

    pass  # divider not supported at root level
    link = fields.get("视频链接", "")
    if link:
        blocks.append(para(f"原视频: {link}"))

    return blocks


def main():
    import argparse
    parser = argparse.ArgumentParser(description="导出分析报告到飞书在线文档")
    parser.add_argument("extracted_dir")
    args = parser.parse_args()

    summary = extract_summary(args.extracted_dir)
    fields = summary.get("fields", {})
    vid = fields.get("视频ID", "unknown")
    title = (fields.get("标题") or f"视频 {vid}")[:60]

    print(f"  创建飞书文档: {title}")
    doc_id = create_doc(f"爆款分析: {title}")
    doc_url = f"https://bytedance.feishu.cn/docx/{doc_id}"

    print("  写入分析内容...")
    blocks = build_doc(fields)
    # 飞书 API 一次最多 50 个 block, 分批写入
    for i in range(0, len(blocks), 40):
        chunk = blocks[i:i+40]
        add_blocks(doc_id, chunk)
        print(f"    写入第 {i+1}-{min(i+40, len(blocks))} 块")

    print(f"  导出成功: {doc_url}")
    print(json.dumps({"ok": True, "doc_url": doc_url, "doc_id": doc_id}, ensure_ascii=False))


if __name__ == "__main__":
    main()
