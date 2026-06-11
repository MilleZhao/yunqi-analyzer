"""
������� HTTP API �� ���� Coze �Ƶ��� / VPS
���: python api_server.py --port 8080
"""
import sys, os, json, subprocess, shutil, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
from urllib.parse import urlparse
from datetime import datetime
from write_to_feishu import extract_summary

WORKDIR = os.path.dirname(os.path.abspath(__file__))

def load_env():
    """���� .env �����ļ�"""
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

ENV_CONFIG = load_env()
PYTHON = sys.executable
FEISHU_BASE = ENV_CONFIG.get("FEISHU_BASE_TOKEN", os.environ.get("FEISHU_BASE_TOKEN", ""))
FEISHU_TABLE = ENV_CONFIG.get("FEISHU_TABLE_ID", os.environ.get("FEISHU_TABLE_ID", ""))
FEISHU_APP_ID = ENV_CONFIG.get("FEISHU_APP_ID", os.environ.get("FEISHU_APP_ID", ""))
FEISHU_APP_SECRET = ENV_CONFIG.get("FEISHU_APP_SECRET", os.environ.get("FEISHU_APP_SECRET", ""))


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok", "time": str(datetime.now())})

        elif self.path in ("/", "/analyzer"):
            file_path = os.path.join(WORKDIR, "website", "analyzer.html")
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self._send_json({"ok": False, "error": "frontend not found"}, 404)
        elif self.path.startswith("/files/"):
            # Serve files from extracted directories
            rel = self.path[len("/files/"):]
            # Security: prevent directory traversal
            if ".." in rel:
                self._send_json({"ok": False, "error": "invalid path"}, 400)
                return
            file_path = os.path.join(WORKDIR, rel)
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                self._send_json({"ok": False, "error": "file not found"}, 404)
                return
            # Determine content type
            ext = os.path.splitext(file_path)[1].lower()
            ctypes = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                      ".mp4": "video/mp4", ".mp3": "audio/mpeg", ".wav": "audio/wav",
                      ".json": "application/json", ".md": "text/markdown", ".csv": "text/csv"}
            content_type = ctypes.get(ext, "application/octet-stream")
            with open(file_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(file_path)}"')
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)

    def do_POST(self):
        body_len = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(body_len)) if body_len else {}

        if self.path == "/webhook":
            # Coze Bot �ص����
            url = body.get("url") or body.get("��������") or ""
            record_id = body.get("record_id", "")
            if not url:
                self._send_json({"ok": False, "error": "missing url"}, 400)
                return

            try:
                result = run_pipeline(url)
                self._send_json({"ok": True, **result})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)


        elif self.path == "/trigger":
            # �첽���� �� Coze fire-and-forget������ 2-5min������ͬ���ȣ�
            url = body.get("url") or body.get("��������") or ""
            if not url:
                self._send_json({"ok": False, "error": "missing url"}, 400)
                return
            thread = threading.Thread(target=run_pipeline_safe, args=(url,), daemon=True)
            thread.start()
            self._send_json({"ok": True, "status": "processing", "url": url})

        elif self.path == "/analyze":
            # ֱ�ӷ�����������ȡĿ¼��
            extracted_dir = body.get("extracted_dir", "")
            if not extracted_dir:
                self._send_json({"ok": False, "error": "missing extracted_dir"}, 400)
                return
            try:
                result = subprocess.run(
                    [PYTHON, "llm_analyze.py", extracted_dir,
         "--provider", config.get("llm_provider","deepseek") if config else "deepseek",
         "--api-key", config.get("llm_api_key","") if config else "",
         "--model", config.get("llm_model","deepseek-chat") if config else "deepseek-chat"],
                    cwd=WORKDIR, capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=300
                )
                if result.returncode == 0:
                    self._send_json({"ok": True, "output": result.stdout[-500:]})
                else:
                    self._send_json({"ok": False, "error": result.stderr[-500:]}, 500)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
        elif self.path == "/pipeline":
            url = body.get("url") or body.get("��������") or ""
            if not url:
                self._send_json({"ok": False, "error": "missing url"}, 400)
                return
            try:
                llm_cfg = body.get("llm_config", {}) or {}
                vision_cfg = body.get("vision_config", {}) or {}
                config = {
                    "llm_provider": llm_cfg.get("provider") or ENV_CONFIG.get("LLM_PROVIDER", "deepseek"),
                    "llm_api_key": llm_cfg.get("api_key") or ENV_CONFIG.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY", ""),
                    "llm_model": llm_cfg.get("model") or ENV_CONFIG.get("LLM_MODEL", "deepseek-chat"),
                    "llm_base_url": llm_cfg.get("base_url") or ENV_CONFIG.get("LLM_BASE_URL", ""),
                    "vision_provider": vision_cfg.get("provider") or ENV_CONFIG.get("VISION_PROVIDER", "ark"),
                    "vision_api_key": vision_cfg.get("api_key") or ENV_CONFIG.get("VISION_API_KEY", ""),
                    "vision_model": vision_cfg.get("model") or ENV_CONFIG.get("VISION_MODEL", "doubao-seed-1-8-251228"),
                    "vision_base_url": vision_cfg.get("base_url") or ENV_CONFIG.get("VISION_BASE_URL", ""),
                }
                feishu_cfg = body.get("feishu_config", {}) or {}
                result = run_pipeline_full(url, config, feishu_cfg)
                self._send_json({"ok": True, **result})
            except Exception as e:
                import traceback; traceback.print_exc()
                self._send_json({"ok": False, "error": str(e)[:500]}, 500)


        elif self.path == "/feishu-doc":
            extracted_dir = body.get("extracted_dir", "")
            if not extracted_dir:
                self._send_json({"ok": False, "error": "missing extracted_dir"}, 400)
                return
            try:
                result = subprocess.run(
                    [PYTHON, "export_feishu_doc.py", extracted_dir],
                    cwd=WORKDIR, capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=30
                )
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if line.strip().startswith("{"):
                            self._send_json(json.loads(line.strip()))
                            return
                    self._send_json({"ok": True, "output": result.stdout[-500:]})
                else:
                    self._send_json({"ok": False, "error": result.stderr[-500:]}, 500)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def run_pipeline(url):
    """��������"""
    logs = []
    # Step 1: ��ȡ
    logs.append("extracting video...")
    proc = subprocess.run(
        ["node", "extract_single.js", url, "--headless"],
        cwd=WORKDIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=120
    )
    if proc.returncode != 0:
        raise RuntimeError(f"extract failed: {proc.stderr[-200:]}")
    logs.append("extract done")

    # Find extracted dir
    extracted_base = os.path.join(WORKDIR, "extracted")
    extracted_dir = None
    if not os.path.isdir(extracted_base):
        raise RuntimeError("extracted dir not found �� extraction may have failed")
    for d in sorted(os.listdir(extracted_base), reverse=True):
        dpath = os.path.join(extracted_base, d)
        if not os.path.isdir(dpath): continue
        mp = os.path.join(dpath, "metadata.json")
        if os.path.exists(mp):
            with open(mp, "r", encoding="utf-8") as f:
                vid = json.load(f).get("video_id", "")
            if vid and vid in url:
                extracted_dir = dpath; break
    if not extracted_dir:
        # fallback
        for d in sorted(os.listdir(extracted_base), reverse=True):
            dpath = os.path.join(extracted_base, d)
            if os.path.isdir(dpath):
                extracted_dir = dpath; break
    if not extracted_dir:
        raise RuntimeError("extracted dir not found")
    logs.append(f"dir: {extracted_dir}")

    # Step 2: �ؼ�֡
    logs.append("extracting keyframes...")
    proc = subprocess.run(
        [PYTHON, "extract_keyframes.py", extracted_dir],
        cwd=WORKDIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60
    )
    logs.append("keyframes done" if proc.returncode == 0 else "keyframes failed")

    # Step 3: ֡����
    logs.append("describing frames...")
    proc = subprocess.run(
        [PYTHON, "describe_frames.py", extracted_dir],
        cwd=WORKDIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=120
    )
    logs.append("describe done" if proc.returncode == 0 else "describe failed")

    # Step 4-5 handled by run_pipeline_full

    # Read result
    meta_path = os.path.join(extracted_dir, "metadata.json")
    video_id = ""
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            video_id = json.load(f).get("video_id", "")


    return {"video_id": video_id, "extracted_dir": extracted_dir, "logs": logs}


def run_pipeline_full(url, config=None, feishu_cfg=None):
    """�������� + ���ؽṹ����������"""
    if config is None:
        config = {}
    # Step 1-3: extract + keyframes + describe
    pipe_result = run_pipeline(url)
    extracted_dir = pipe_result["extracted_dir"]

    # Step 4: LLM analysis with user's API config
    llm_provider = config.get("llm_provider") or ENV_CONFIG.get("LLM_PROVIDER", "deepseek")
    llm_key = config.get("llm_api_key") or ENV_CONFIG.get("LLM_API_KEY", "")
    llm_model = config.get("llm_model") or ENV_CONFIG.get("LLM_MODEL", "deepseek-chat")
    llm_base = config.get("llm_base_url") or ENV_CONFIG.get("LLM_BASE_URL", "")

    pipe_result.setdefault("logs", []).append(f"llm analyzing with {llm_provider}/{llm_model}...")
    llm_cmd = [PYTHON, "llm_analyze.py", extracted_dir,
               "--provider", llm_provider,
               "--api-key", llm_key,
               "--model", llm_model]
    if llm_base:
        llm_cmd += ["--base-url", llm_base]
    proc = subprocess.run(
        llm_cmd,
        cwd=WORKDIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300
    )
    if proc.returncode != 0:
        raise RuntimeError(f"LLM analysis failed: {proc.stderr[-300:]}")
    pipe_result["logs"].append("analysis done")

    # Step 5: write to Feishu (use config from request, fallback to env)
    feishu_base = feishu_cfg.get("base_token") or FEISHU_BASE
    feishu_table = feishu_cfg.get("table_id") or FEISHU_TABLE
    if feishu_base:
        pipe_result["logs"].append("writing to feishu...")
        try:
            subprocess.run(
                [PYTHON, "write_to_feishu.py", extracted_dir,
                 "--base-token", feishu_base, "--table-id", feishu_table, "--skip-if-exists"],
                cwd=WORKDIR, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=30
            )
            pipe_result["logs"].append("feishu done")
        except Exception as e:
            pipe_result["logs"].append(f"feishu skipped: {e}")

    # Read structured data using extract_summary
    try:
        summary = extract_summary(extracted_dir)
        fields = summary.get("fields", {})
    except Exception:
        fields = {}

    # Collect available asset files
    assets = {}
    if os.path.isdir(extracted_dir):
        for fname in os.listdir(extracted_dir):
            fpath = os.path.join(extracted_dir, fname)
            if os.path.isfile(fpath):
                rel = os.path.relpath(fpath, WORKDIR).replace(os.sep, "/")
                ext = os.path.splitext(fname)[1].lower()
                if ext in (".mp4", ".mov", ".webm"):
                    assets["video"] = rel
                elif ext in (".mp3", ".wav", ".m4a", ".aac"):
                    assets["audio"] = rel
                elif fname == "cover.jpg" or fname == "cover.png":
                    assets["cover"] = rel
            elif os.path.isdir(fpath) and fname == "keyframes":
                kf_files = sorted([os.path.join("keyframes", kf) for kf in os.listdir(fpath) if kf.endswith(".jpg")])
                if kf_files:
                    assets["keyframes"] = os.path.relpath(os.path.join(extracted_dir, "keyframes"), WORKDIR).replace(os.sep, "/")
                    assets["keyframe_count"] = len(kf_files)
        # Subtitles/captions from metadata description
        meta_path = os.path.join(extracted_dir, "metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as mf:
                meta = json.load(mf)
            desc = meta.get("description", "")
            if desc:
                assets["subtitle_text"] = desc[:2000]

    return {
        "video_id": pipe_result["video_id"],
        "extracted_dir": extracted_dir,
        "fields": fields,
        "assets": assets,
        "logs": pipe_result.get("logs", [])
    }

def run_pipeline_safe(url):
    """���쳣����ĺ�̨������� �� �����첽 /trigger"""
    try:
        result = run_pipeline(url)
        print(f"[trigger] ���: {result.get('video_id', '?')}")
    except Exception as e:
        print(f"[trigger] ʧ��: {url} �� {e}")
        import traceback; traceback.print_exc()


if __name__ == "__main__":
    port = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "--port" else 8080
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"API Server running on port {port}")
    print(f"Endpoints: GET /health | POST /trigger | POST /webhook | POST /analyze")
    server.serve_forever()










