# 抖音爆款分析全流程

## 前置条件
`
cd C:\Users\LENOVO\Documents\云阙智能1
`

---

## 一条命令跑通全部

`powershell
# 提取 + 关键帧 + LLM输入 + 自动打开拼贴图 + 打印元数据摘要
python run_pipeline.py "https://www.douyin.com/video/<VIDEO_ID>

# 变体
python run_pipeline.py "https://www.douyin.com/video/<VIDEO_ID>" --no-video   # 跳过视频下载
python run_pipeline.py "https://www.douyin.com/video/<VIDEO_ID>" --headless  # 无头模式
`

管线结束时自动：
- 打印元数据摘要（作者、数据、标签、BGM）
- 打开关键帧拼贴图（默认图片查看器）
- 提示 LLM 输入文件和分析文件路径

---

## 验证

`powershell
# 搜 [pending analysis] 即空壳 → 需手动补写
Select-String -Path extracted\*\viral_analysis.md -Pattern "pending analysis"
`

---

## 撰写分析

管线的 llm_input.md 是给 AI 用的分析素材。撰写分析时手动写入 extracted/<VIDEO_ID>/viral_analysis.md。

分析框架参考 iral_analysis_prompt.txt（四维度：爆款元素拆解 → 受众画像 → 归因 → 复用建议），完整范例参考 extracted/7618932623473882801/viral_analysis.md。

---

## 关键文件

| 文件 | 作用 |
|---|---|
| un_pipeline.py | 管线主控（已清理空壳函数，加自动素材展示） |
| extract_single.js | Playwright 浏览器提取抖音 SSR 数据 |
| extract_keyframes.py | ffmpeg 提取视频关键帧 / 复用幻灯片 |
| iral_analysis_prompt.txt | 爆款分析的四维度提示词框架 |
| PITFALLS.md | 12 条踩坑记录 + 避坑指南 |
| douyin_profile/ | 浏览器持久化目录（含登录态 Cookies） |
