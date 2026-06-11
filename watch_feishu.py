"""
飞书待处理队列监控 — 自动检测抖音链接 → 提取 → 分析 → 写入
用法: python watch_feishu.py [--interval 30]
依赖: DEEPSEEK_API_KEY, FEISHU_BASE_TOKEN 环境变量
"""
import sys, os, json, subprocess, time, traceback
from datetime import datetime

CLI = os.path.expanduser("~/go/bin/cli.exe" if platform.system() == "Windows" else "~/go/bin/cli")
WORKDIR = os.path.dirname(os.path.abspath(__file__))
BASE_TOKEN = os.environ.get("FEISHU_BASE_TOKEN", "RlGBbQpxBalchssDFJbcuBjGnee")
QUEUE_TABLE = "tblo7p6qiglky8g5"
RESULT_TABLE = "tbllt7XfgHBPcdvS"


def run_lark(*args):
    """执行 lark-cli 命令"""
    cmd = [CLI] + [str(a) for a in args]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    if proc.returncode != 0 and proc.stderr.strip():
        print(f"  [lark] {proc.stderr[:120]}")
    if proc.stdout and proc.stdout.strip():
        return json.loads(proc.stdout)
    return {}


def get_pending():
    """获取待处理的记录列表"""
    result = run_lark(
        "base", "+record-list",
        "--base-token", BASE_TOKEN,
        "--table-id", QUEUE_TABLE,
        "--format", "json",
        "--limit", "10",
    )
    records = []
    data_rows = result.get("data", {}).get("data", [])
    rid_list = result.get("data", {}).get("record_id_list", [])
    field_order = result.get("data", {}).get("fields", [])

    for i, row in enumerate(data_rows):
        # Parse row as a dict by field order
        rec = dict(zip(field_order, row))
        status = rec.get("状态", "")
        # Select field returns a list like ["待处理"]
        if isinstance(status, list):
            status = status[0] if status else ""
        if status == "待处理":
            url = rec.get("抖音链接", "")
            if isinstance(url, list): url = url[0] if url else ""
            records.append({
                "record_id": rid_list[i] if i < len(rid_list) else "",
                "url": url,
                "video_id": rec.get("视频ID", "") or "",
                "note": rec.get("备注", "") or "",
            })
    return records


def update_status(record_id, status, video_id="", note=""):
    """更新记录的字段"""
    fields = {"状态": status}
    if video_id:
        fields["视频ID"] = video_id
    if note:
        fields["备注"] = note[:500]
    run_lark(
        "base", "+record-upsert",
        "--base-token", BASE_TOKEN,
        "--table-id", QUEUE_TABLE,
        "--record-id", record_id,
        "--json", json.dumps(fields, ensure_ascii=False),
    )


def run_step(cmd_list, desc):
    """执行一步，返回 (success, output)"""
    print(f"  >> {desc}")
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(cmd_list, cwd=WORKDIR, capture_output=True, env=env,
                            text=True, encoding="utf-8", errors="replace", timeout=300)
        if proc.returncode != 0:
            print(f"  [FAIL] {proc.stderr[-200:] if proc.stderr else 'unknown'}")
            return False, proc.stderr or ""
        return True, proc.stdout or ""
    except Exception as e:
        return False, str(e)


def process_one(record):
    """处理一条待处理记录"""
    rid = record["record_id"]
    url = record["url"]
    if not url:
        update_status(rid, "失败", note="链接为空")
        return

    update_status(rid, "处理中")
    print(f"\n{'='*50}\n处理: {url[:60]}\n{'='*50}")

    try:
        # Step 1: 提取视频
        ok, out = run_step(["node", "extract_single.js", url, "--headless"], "Step 1/4: 提取视频")
        if not ok:
            update_status(rid, "失败", note=f"提取失败: {out[-200:]}")
            return

        # 找到刚提取的目录（按 video_id 精确匹配）
        extracted_base = os.path.join(WORKDIR, "extracted")
        extracted_dir = None
        for d in sorted(os.listdir(extracted_base), reverse=True):
            dpath = os.path.join(extracted_base, d)
            if not os.path.isdir(dpath):
                continue
            meta_path = os.path.join(dpath, "metadata.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8", errors="replace") as f:
                        vid = json.load(f).get("video_id", "")
                    if vid and vid in url:
                        extracted_dir = dpath
                        break
                except:
                    pass
        # fallback: 使用最新目录
        if not extracted_dir:
            for d in sorted(os.listdir(extracted_base), reverse=True):
                dpath = os.path.join(extracted_base, d)
                if os.path.isdir(dpath):
                    extracted_dir = dpath
                    break
        if not extracted_dir:
            update_status(rid, "失败", note="提取目录未找到")
            return
        print(f"  目录: {extracted_dir}")

        # Step 2: 关键帧
        ok, out = run_step(["python", "extract_keyframes.py", extracted_dir], "Step 2/4: 关键帧")
        if not ok:
            update_status(rid, "失败", note=f"关键帧失败: {out[-200:]}")
            return

        # Step 3: 关键帧描述
        ok, out = run_step(["python", "describe_frames.py", extracted_dir], "Step 3/4: 帧描述")
        if not ok:
            print("  (帧描述失败，继续...)")

        # Step 4: DeepSeek 分析
        try:
            ok, out = run_step(["python", "deepseek_analyze.py", extracted_dir], "Step 4/4: DeepSeek 分析")
            if not ok:
                print(f"  (DeepSeek 分析失败，继续写入基础数据)")
        except Exception as ds_e:
            print(f"  (DeepSeek 异常: {ds_e})")

        # 写入飞书
        print("  写入飞书...")
        wf_env = os.environ.copy()
        wf_env["PYTHONIOENCODING"] = "utf-8"
        subprocess.run(
            ["python", "write_to_feishu.py", extracted_dir,
             "--base-token", BASE_TOKEN, "--table-id", RESULT_TABLE, "--skip-if-exists"],
            cwd=WORKDIR, capture_output=True, timeout=30, env=wf_env
        )

        # 获取视频ID
        meta_path = os.path.join(extracted_dir, "metadata.json")
        video_id = ""
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8", errors="replace") as f:
                video_id = json.load(f).get("video_id", "")

        update_status(rid, "已完成", video_id=video_id)
        print(f"  ✅ 完成: {video_id}")

    except Exception as e:
        err = f"{type(e).__name__}: {str(e)[:300]}"
        traceback.print_exc()
        update_status(rid, "失败", note=err)


def main():
    interval = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "--interval" else 30

    print(f"🚀 监控启动 — 每 {interval}s 检查")
    print(f"   待处理表: {QUEUE_TABLE}")
    print(f"   结果表: {RESULT_TABLE}")
    print(f"   DeepSeek: {'✅' if os.environ.get('DEEPSEEK_API_KEY') else '❌ 未设置'}")

    while True:
        try:
            records = get_pending()
            if records:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 发现 {len(records)} 条待处理")
                for rec in records:
                    process_one(rec)
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 无待处理", end="\r")
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n停止监控")
            break
        except Exception as e:
            print(f"\n[错误] {e}")
            time.sleep(interval)


if __name__ == "__main__":
    main()


