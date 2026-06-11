"""
关键帧提取器 v3 — 并行提速版
支持视频+图文+仅封面三种模式
提速: ffmpeg 场景检测 + 间隔采样并行执行
"""
import sys, os, json, subprocess, glob, shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_ffmpeg(args, desc=""):
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + args
    print(f"  [{desc}] ffmpeg ...")
    subprocess.run(cmd, capture_output=True)
    return True

def extract_keyframes(video_dir, scene_threshold=0.3, interval_sec=3):
    video_path = os.path.join(video_dir, "video.mp4")
    metadata_path = os.path.join(video_dir, "metadata.json")
    cover_path = os.path.join(video_dir, "cover.jpg")
    keyframes_dir = os.path.join(video_dir, "keyframes")
    os.makedirs(keyframes_dir, exist_ok=True)

    # 模式1: 有视频文件 — ffmpeg 场景检测 + 间隔采样并行
    if os.path.exists(video_path):
        print("视频模式: ffmpeg 场景检测 + 间隔采样 (并行)")
        duration = 60
        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8", errors="replace") as f:
                meta = json.load(f)
            duration = meta.get("duration_ms", 60000) / 1000
        print(f"  时长: {duration:.1f}s")

        scene_dir = os.path.join(keyframes_dir, "_scene")
        interval_dir = os.path.join(keyframes_dir, "_interval")
        os.makedirs(scene_dir, exist_ok=True)
        os.makedirs(interval_dir, exist_ok=True)

        # 并行执行两个 ffmpeg
        scene_args = ["-i", video_path, "-vf", f"select='gt(scene,{scene_threshold})'",
                      "-vsync", "vfr", "-qscale:v", "3", os.path.join(scene_dir, "scene_%03d.jpg")]
        interval_args = ["-i", video_path, "-vf", f"fps=1/{interval_sec}",
                         "-qscale:v", "3", os.path.join(interval_dir, "interval_%03d.jpg")]

        t_ffmpeg = __import__('time').time()
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(run_ffmpeg, scene_args, "场景检测"): "scene",
                executor.submit(run_ffmpeg, interval_args, "间隔采样"): "interval",
            }
            for future in as_completed(futures):
                label = futures[future]
                try:
                    future.result()
                    print(f"  [{label}] 完成")
                except Exception as e:
                    print(f"  [{label}] 失败: {e}")
        print(f"  ffmpeg 并行耗时: {__import__('time').time() - t_ffmpeg:.1f}s")

        # 合并帧
        all_frames = []
        for d in [scene_dir, interval_dir]:
            for f in sorted(os.listdir(d)):
                if f.endswith(".jpg"):
                    all_frames.append(os.path.join(d, f))
        # 去重（两个通道可能有重复帧）
        seen = set()
        unique_frames = []
        for src in all_frames:
            name = os.path.basename(src)
            if name not in seen:
                seen.add(name)
                unique_frames.append(src)
            else:
                # 同名冲突：给一个不同的编号
                base, ext = os.path.splitext(name)
                for suffix in range(1, 100):
                    new_name = f"{base}_{suffix}{ext}"
                    if new_name not in seen:
                        seen.add(new_name)
                        dst_dup = os.path.join(os.path.dirname(src), new_name)
                        shutil.copy2(src, dst_dup)
                        unique_frames.append(dst_dup)
                        break

        for i, src in enumerate(sorted(unique_frames)):
            shutil.move(src, os.path.join(keyframes_dir, f"frame_{i+1:03d}.jpg"))
        for d in [scene_dir, interval_dir]:
            if os.path.exists(d):
                shutil.rmtree(d)

    # 模式2: 图文幻灯片
    slides = sorted(glob.glob(os.path.join(video_dir, "slide_*.jpg")))
    if slides:
        print(f"图文模式: {len(slides)} 张幻灯片")
        for i, s in enumerate(slides):
            dst = os.path.join(keyframes_dir, f"frame_{i+1:03d}.jpg")
            if s != dst:
                shutil.copy2(s, dst)

    # 模式3: 仅封面兜底
    frames = [f for f in os.listdir(keyframes_dir) if f.endswith(".jpg") and not f.startswith("_")]
    if not frames and os.path.exists(cover_path):
        print("仅封面模式")
        shutil.copy2(cover_path, os.path.join(keyframes_dir, "frame_001.jpg"))

    frames = [f for f in os.listdir(keyframes_dir) if f.endswith(".jpg") and not f.startswith("_")]
    print(f"\n关键帧: {len(frames)} 张 -> {keyframes_dir}")
    for f in sorted(frames):
        print(f"  {f}")

    # 生成拼贴图（网络图快，这里不阻塞管线）
    if len(frames) >= 4:
        try:
            from PIL import Image
            sample = sorted(glob.glob(os.path.join(keyframes_dir, "frame_*.jpg")))[:16]
            imgs = [Image.open(f).resize((200, 112)) for f in sample]
            cols = min(4, len(imgs))
            rows = (len(imgs) + cols - 1) // cols
            mosaic = Image.new("RGB", (cols * 200, rows * 112))
            for idx, img in enumerate(imgs):
                mosaic.paste(img, ((idx % cols) * 200, (idx // cols) * 112))
            mosaic.save(os.path.join(keyframes_dir, "_mosaic.jpg"), quality=45)
            print("  拼贴图: _mosaic.jpg")
        except ImportError:
            pass

    return keyframes_dir

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python extract_keyframes.py <目录> [--scene 0.4] [--interval 3]")
        sys.exit(1)
    d = sys.argv[1]
    if not os.path.isdir(d):
        print("目录不存在:", d)
        sys.exit(1)
    scene = 0.3
    interval = 3
    for i, a in enumerate(sys.argv):
        if a == "--scene" and i + 1 < len(sys.argv):
            scene = float(sys.argv[i + 1])
        if a == "--interval" and i + 1 < len(sys.argv):
            interval = float(sys.argv[i + 1])
    result = extract_keyframes(d, scene, interval)
    if result:
        n = len([f for f in os.listdir(result) if f.endswith(".jpg") and not f.startswith("_")])
        print(f"\nKEYFRAMES_DIR={result}")
    else:
        sys.exit(1)
