# 踩坑日志 — 前端 Analyzer 开发

## 1. Math.random() 导致同一链接每次互动数据不同
- **现象**：输入同一个视频链接，每次点击"一键分析"返回的点赞/评论/分享/收藏数值随机变化
- **原因**：`generateDemoResult` 中 `var idx=Math.floor(Math.random()*5)` 每次调用产生不同随机数
- **修复**：改为 `hashStr(vid)%5`，基于视频 ID 做确定性哈希取模。后续彻底移除模拟数据，改为调真实 API

## 2. 所有文本字段（标题/作者/文案）硬编码，换链接后显示完全一样
- **现象**：输入不同视频链接，分析结果中标题、作者、钩子文案、内容结构等文本完全不变
- **原因**：`generateDemoResult` 中 title、author、hook_3s 等字段全部写死为静态字符串，仅互动数值按 hash 变化
- **修复**：移除模拟数据生成逻辑，改为调用 `api_server.py` 的 `/pipeline` 端点获取真实管线分析结果

## 3. 前端 fetch 调用 /analyze 端点但参数不匹配
- **现象**：前端 POST `/analyze` 传了 `{url}`，但 API 的 `/analyze` 端点实际需要 `{extracted_dir}`
- **原因**：端点语义不一致——`/analyze` 是给已有提取目录用的离线分析，不是完整管线入口
- **修复**：新增 `POST /pipeline` 端点，接收 `{url}` 参数，内部调 `run_pipeline_full()` → 跑完整管线 → 调 `extract_summary()` 读取结构化字段 → 返回 JSON

## 4. URL 解析只匹配 /video/(\d+) 格式
- **现象**：短链接（v.douyin.com）、用户页 modal_id 参数、纯数字 ID 输入均无法提取视频 ID
- **原因**：正则 `url.match(/video\/(\d+)/)` 只能识别标准视频页链接
- **修复**：新增 `extractVideoId()` 函数，依次尝试 /video/(\d+)、modal_id=(\d+)、/note/(\d+)、纯数字格式

## 5. API 不可用时静默降级为假数据
- **现象**：`api_server.py` 未启动时，前端静默 fallback 到 `generateDemoResult()`，用户看到的是假数据却以为是真实分析
- **原因**：`catch(e){}` 空回调吞掉了 fetch 错误，然后无条件走 `if(!result)result=generateDemoResult(url)`
- **修复**：改为显式检测 fetch/NetworkError，弹出明确提示「无法连接 API 服务器，请先运行: python api_server.py --port 8080」

## 6. innerHTML 拼接未做 HTML 转义
- **现象**：如果 API 返回的标题/文案包含 `<` `>` `&` 等字符，会导致 HTML 注入或渲染异常
- **修复**：新增 `escHtml()` 函数，渲染前对 `& < > "` 做转义

## 7. duplicate setStep(5) 调用导致步骤动画闪烁
- **原因**：修 `setAllDone` 时残留了旧版 `setStep(5)` 调用，导致步骤 5 先亮为 current 再被 setAllDone 覆写
- **修复**：移除重复的 `setStep(5)` 调用，仅保留 `setAllDone()`

## 8. fetch 无超时控制，API 不可用时长时间挂起
- **现象**：请求发到 localhost:8080 但服务未启动时，浏览器默认超时可达 30-90 秒
- **修复**：添加 `AbortController`，3 秒超时自动中断 fetch

## 9. run_pipeline 引用未定义的 config 变量导致 NameError
- **现象**：前端显示"API 返回错误"，实际是后端 `run_pipeline` 在第 4 步 LLM 分析处抛 `NameError: name 'config' is not defined`
- **原因**：给 `run_pipeline` 加了 `config.get("llm_provider")` 等引用，但函数签名是 `def run_pipeline(url)`，没接收 config 参数。`run_pipeline_full` 调 `run_pipeline(url)` 时 config 传不进去
- **修复**：重构管线分层——`run_pipeline` 只做步骤 1-3（提取 + 关键帧 + 帧描述），LLM 分析和飞书写入移到 `run_pipeline_full` 中执行，config 在此层传入

## 10. CORS 预检 OPTIONS 请求未处理
- **现象**：`file://` 协议页面发 POST + `Content-Type: application/json` 时，浏览器先发 OPTIONS 预检，服务器不响应导致 POST 被拦截，前端显示"无法连接 API 服务器"（实际服务器在运行）
- **原因**：`BaseHTTPRequestHandler` 只实现了 `do_GET` / `do_POST`，没有 `do_OPTIONS`
- **修复**：新增 `do_OPTIONS` 返回 204 + `Access-Control-Allow-Origin: *` + `Allow-Methods` + `Allow-Headers`

## 11. HTTPServer 单线程阻塞健康检查
- **现象**：管线运行期间（2-5 分钟），`/health` 端点无响应，前端状态指示灯变红
- **原因**：`HTTPServer` 单线程处理请求，管线阻塞期间无法响应其他请求
- **修复**：改为 `ThreadingHTTPServer`（`ThreadingMixIn + HTTPServer`），`daemon_threads = True`

## 12. LLM 输出的 Markdown 格式原样显示在前端
- **现象**：拍摄手法显示 `- **镜头**: 幻灯片式...`，内容结构显示 `- **段落划分**: 三段式...`，**加粗标记和列表符号裸露
- **原因**：`extract_summary` 用正则从 `viral_analysis.md` 提取字段时，LLM 的 Markdown 输出格式（`**加粗**`、`- 列表项`）被原样捕获，前端直接 `innerHTML` 显示
- **修复**：新增 `strip_md()` 函数，去除 `**加粗**`、`- 列表`、`# 标题`、`---` 分隔线等 Markdown 标记，对所有文本字段统一清洗后再返回

## 13. shoot_style 空值时 fallback 到 content_struct
- **现象**：拍摄手法字段显示的是内容结构的内容
- **原因**：`if not shoot_style: shoot_style = content_struct` 将两个不同维度的数据混在一起
- **修复**：移除 fallback，shoot_style 为空时保持空字符串

## 14. 爆款等级卡片展示完整标题导致布局溢出
- **现象**：长标题（如"破解 read the room | 异想Hit #异想hit..."）全部展示在等级卡片中
- **修复**：前端截断标题到 60 字符，超出加省略号

## 15. _fix_md2.py 替换 strip_md 时误删 grade_by_likes 等四个函数
- **现象**：分析完成后前端"什么数据都显示不出来"，后端 `extract_summary` 抛 `NameError: name 'grade_by_likes' is not defined`
- **原因**：`_fix_md2.py` 用 `c.find("def strip_md")` 到 `c.find("def extract_summary")` 定位替换范围，但 strip_md 是之前插入在 grade_by_likes / run_lark / ensure_table / extract_text_block 之前的，整个区间被一起覆盖删除
- **修复**：手动恢复四个函数，同时用更精准的定位方式（只替换 strip_md 函数体本身）
- **教训**：用 `c.find("def xxx")` 做区间替换时，必须确认区间内只有目标函数，不能包含其他定义

## 16. strip_md 修复后 return 语句中的 strip_md() 调用被覆盖丢失
- **现象**：Markdown 格式再次出现（修复 #15 后恢复的函数把之前加的 strip_md() 调用覆盖了）
- **修复**：重新对 return 语句中的 7 个文本字段应用 strip_md() 包装

## 17. 下载选项语义混淆：勾选控制的是"是否分析"而非"是否下载"
- **现象**：用户勾选"视频文件""音频文件"等选项，以为会下载到本地，实际只是传给 API 作为分析参数
- **修复**：选项标签改为"下载视频/下载音频/...", 底部加提示"勾选的内容将在分析完成后提供下载"。新增 GET /files 端点提供文件下载、/pipeline 响应附加 assets 字段列出可用素材路径，分析完成后按勾选显示下载按钮

## 17. llm_analyze.py DeepSeek Base URL 多加 /v1 导致 401
- **现象**：前面版本分析正常，重构为 llm_analyze.py 后一直 401「API Key 无效」
- **原因**：原始 deepseek_analyze.py 用的是 `https://api.deepseek.com/chat/completions`，重构时误改为 `https://api.deepseek.com/v1/chat/completions`。DeepSeek 的 /v1 路径认证方式不同，导致 API Key 被拒
- **修复**：恢复为 `https://api.deepseek.com/chat/completions`
- **教训**：重构时保留已验证的配置值，不要顺手"优化"

## 18. llm_analyze.py 环境变量名不兼容：LLM_API_KEY vs DEEPSEEK_API_KEY
- **现象**：前面版本用 deepseek_analyze.py 分析正常，换 llm_analyze.py 后提示「未配置 LLM API Key」（#17 修完 URL 仍无效）
- **原因**：原 deepseek_analyze.py 读 `DEEPSEEK_API_KEY` 环境变量，重构后的 llm_analyze.py 只认 `LLM_API_KEY`。用户的环境变量里设的是 `DEEPSEEK_API_KEY`，新代码读不到
- **修复**：llm_analyze.py 和 api_server.py 的 API Key 读取链都加上 `os.environ.get("DEEPSEEK_API_KEY", "")` 作为最后一层兜底
- **教训**：重构变量名时必须兼容旧名，不能假设用户会跟着改名

## 19. 下载按钮 DOM 插入破坏 HTML 结构 + null.style 崩溃
- **现象**：分析完成后前端报 "cannot read nullstyle"，结果不显示
- **原因**：插入 downloadRow 时用 `</div></div></div>` 做锚点替换，该模式在文件中出现 3 次，可能匹配到了错误位置破坏了 resultsPanel 的 DOM 结构，导致 downloadRow / dlVideo 等元素未挂载到文档中
- **修复**：所有 `.style` 访问前加 null 守卫 (`if(!el)return` / `(el||{}).style`)
- **教训**：用重复字符串做替换锚点极易误匹配，应该用唯一 id 或 class 定位

## 20. 分析提示词缺少"核心洞察"和"目标受众"维度
- **现象**：飞书表格和前端 UI 的"核心洞察""目标受众"始终为空
- **原因**：`viral_analysis_prompt.txt` 只定义了 6 个分析维度（钩子/结构/情绪/拍摄/CTA/复用），不包含这两个字段。LLM 不会凭空输出
- **修复**：提示词从 6 维度扩展为 8 维度，新增第 3 节"目标受众"和第 5 节"核心洞察"，输出格式同步更新。`extract_summary` 的正则和章节号全部适配

## 21. 下载按钮 DOM 插入锚点歧义导致不可见
- **现象**：分析完成后找不到视频/音频等文件的下载入口，只能看到 CSV 导出
- **原因**：downloadRow 插入时用 `</div></div></div>` 做锚点（文件中出现 3 次），误匹配到错误位置
- **修复**：用唯一按钮 onclick 属性做锚点重插，并给下载行加分隔线和加粗标题
