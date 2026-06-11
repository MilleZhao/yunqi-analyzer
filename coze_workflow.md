# 抖音爆款分析 - Coze工作流完整配置 (修正版)

## 整体架构

```
  1.开始 -> 2.HTTP -> [条件] -> 3.Code -> 4.HTTP -> 5.Code
             无水印     code=200?   拆字段    视频理解    拼装素材
             解析API

  5.Code -> [cover?] -> 6.LLM视觉 -> 7.LLM文本 -> 8a.Token -> 8b+8c -> 9.结束
                          封面分析    8维度爆款    飞书鉴权    回写表格
```

预计单次耗时: 30-50秒

---

## 前置准备 (一次性, 约20分钟)

### 1. 注册抖音无水印解析 API

推荐: 维易API (weiyiapi.com) / 猪猪API (zzapi.cn) / Roll API (rollapi.com)
注册后在控制台找到: API地址 + API Key

### 2. 注册视频理解 API

推荐: 图普科技 (tuputech.com) - 传入视频URL直接返回分镜描述
备选: 阿里云视频AI (aliyun.com) - AppCode鉴权

### 3. 飞书开放平台配置

open.feishu.cn -> 创建企业自建应用 -> 权限: bitable:app
记录: APP_ID / APP_SECRET / BASE_TOKEN / TABLE_ID
在Coze工作流变量中存储: FEISHU_APP_ID / FEISHU_APP_SECRET

---

## 飞书多维表格字段设计

| 字段名 | 类型 | 说明 |
|--------|------|------|
| 抖音链接 | 文本 | 用户输入的原始链接 |
| 视频标题 | 文本 | |
| 作者 | 文本 | |
| 点赞数 | 数字 | |
| 评论数 | 数字 | |
| 分享数 | 数字 | |
| 收藏数 | 数字 | |
| 标签 | 文本 | |
| BGM | 文本 | |
| 封面分析 | 长文本 | LLM视觉分析封面 |
| 八维度分析报告 | 长文本 | 完整Markdown报告 |
| 分析状态 | 单选 | 处理中/已完成/失败 |
| 分析时间 | 日期 | |

---

## 节点配置

### 节点1 - 开始

类型: Start

| 变量名 | 类型 | 必填 | 说明 |
|--------|------|:---:|------|
| douyin_url | string | 是 | 抖音分享链接 (v.douyin.com/xxx) |
| feishu_record_id | string | 否 | 飞书表格行ID (webhook触发时自带) |

---

### 节点2 - HTTP: 抖音无水印解析

类型: HTTP Request

```
方法: GET
URL: 你注册的API地址
参数:
  url = {{节点1.douyin_url}}
  key = 你的API_KEY
```

期望返回:
```
{
  code: 200,
  data: {
    title: 视频标题,
    desc: 视频文案,
    video_url: https://xxx.mp4,
    cover_url: https://xxx.jpg,
    author_name: 作者昵称,
    music_title: BGM名称,
    digg_count: 12345,
    comment_count: 234,
    share_count: 567,
    collect_count: 89,
    hashtags: [标签1, 标签2]
  }
}
```

### [Bug1修复] 条件分支: 节点2返回 code != 200 ?

如果API返回code不是200, 直接跳转到结束节点, 输出status=解析失败。

---

### 节点3 - Code: 拆字段

类型: Code (Python)

输入: {{节点2.body}}

```python
def main(result: dict) -> dict:
    d = result.get("data", result)

    def g(key, default=""):
        return d.get(key, default)

    digg = max(int(g("digg_count", 0)), 1)

    hashtags = g("hashtags", [])
    if isinstance(hashtags, list):
        tags_str = " ".join(["#" + t for t in hashtags if t])
    else:
        tags_str = str(hashtags) if hashtags else ""

    return {
        "video_url": g("video_url"),
        "cover_url": g("cover_url"),
        "title": g("title"),
        "desc": g("desc"),
        "author": g("author_name"),
        "bgm": g("music_title"),
        "digg": int(g("digg_count", 0)),
        "comment": int(g("comment_count", 0)),
        "share": int(g("share_count", 0)),
        "collect": int(g("collect_count", 0)),
        "share_rate": round(int(g("share_count",0))/digg*100, 1),
        "collect_rate": round(int(g("collect_count",0))/digg*100, 1),
        "comment_rate": round(int(g("comment_count",0))/digg*100, 1),
        "tags": tags_str,
    }
```

### Bug修复: API字段名映射

不同API返回字段名不同, 修改节点3里 g() 的key参数即可。例如:
- 昵称叫nickname: 改 g("nickname")
- 点赞数叫likes: 改 g("likes")
---

### 节点4 - HTTP: 视频理解 API

类型: HTTP Request

方案A - 图普科技 (推荐)

```
方法: POST
URL: https://api.tuputech.com/video/analysis
Headers:
  Content-Type: application/json
  Authorization: 你的API_KEY
Body: { video_url: 节点3.video_url, scene: shot }
超时: 90秒
```

方案B - 阿里云视频AI (备选)

```
方法: POST
URL: https://videoseg.cn-shanghai.aliyuncs.com/
Query: Action=SubmitShotDetectionJob
Headers: Authorization: APPCODE 你的AppCode
Body: { VideoUrl: 节点3.video_url }
```

期望返回:
```
{
  shots: [
    { start_time: 0.0, end_time: 3.2, description: 开头大字..., tags: [教育] },
    ...
  ]
}
```

### [Bug2+Bug3修复] 节点4失败时的兜底

如果节点4超时或返回error, 节点5会检测到并降级为纯文本+封面分析。
video_url为空时跳过节点4, 节点5直接用空关键帧。
---

### 节点5 - Code: 拼装素材 (含Bug3+Bug7修复)

类型: Code (Python)

输入: {{节点3}} + {{节点4.body}}

```python
def main(video_result: dict, parsed: dict) -> dict:
    # Bug3修复: 检测视频理解是否成功
    shots = []
    error = None
    if isinstance(video_result, dict):
        shots = video_result.get("shots",
                 video_result.get("data", {})
                 .get("shots", []))
        error = video_result.get("error")

    # Bug7修复: 截断过长描述 (总字数限制3000)
    MAX_CHARS = 3000
    frames_text = ""
    total = 0

    if error:
        frames_text = f"(视频理解失败: {error[:100]})"
    elif not shots:
        frames_text = "(未提取到关键帧, 请基于封面和文案分析)"
    else:
        for i, shot in enumerate(shots[:12]):
            desc = shot.get("description", "")[:200]
            start = shot.get("start_time", 0)
            line = f"- 第{i+1}帧 ({start:.1f}s): {desc}
"
            if total + len(line) > MAX_CHARS:
                frames_text += f"(后续 {len(shots)-i} 帧已省略)
"
                break
            frames_text += line
            total += len(line)

    user_msg = (
        f"# 视频基本信息
"
        f"标题: {parsed['title']}
"
        f"文案: {parsed['desc']}
"
        f"作者: {parsed['author']}
"
        f"BGM: {parsed['bgm']}
"
        f"标签: {parsed['tags']}

"
        f"## 互动数据
"
        f"| 指标 | 数值 |
"
        f"|---|---|
"
        f"| 点赞 | {parsed['digg']:,} |
"
        f"| 评论 | {parsed['comment']:,} |
"
        f"| 分享 | {parsed['share']:,} |
"
        f"| 收藏 | {parsed['collect']:,} |
"
        f"| 评论率 | {parsed['comment_rate']}% |
"
        f"| 分享率 | {parsed['share_rate']}% |
"
        f"| 收藏率 | {parsed['collect_rate']}% |

"
        f"## 关键帧画面描述 (共{len(shots)}帧)
"
        f"{frames_text}"
    )

    return {
        "user_message": user_msg,
        "frame_count": len(shots),
        "has_frames": len(shots) > 0 and not error,
        **parsed,
    }
```

### Bug修复说明

- **Bug3**: 检测 error 字段, 失败时明确告知LLM
- **Bug7**: MAX_CHARS=3000 限制关键帧总字数, 单帧截断200字
- **Bug2**: video_url为空时 shots=[], 自动降级
---

### [条件分支] 封面URL存在?

如果 {{节点3.cover_url}} 非空 -> 走节点6
如果为空 -> 跳过节点6, 直接走节点7

---

### 节点6 - LLM: 封面视觉分析

类型: LLM

模型: GPT-4o / Claude 3.5 Sonnet (选支持视觉的)

系统提示词:
```
你是一个抖音短视频内容分析师。请分析这张视频封面：
1. 画面上有什么文字（逐字读出）
2. 视觉元素：人物、产品、场景
3. 色彩风格和排版特点（大字报？清新文艺？数据图表？）
4. 这帧作为封面钩子的叙事功能——它想让用户产生什么心理反应？

用3句中文概述，不加格式。
```

用户消息 (多模态):
- 图片: {{节点3.cover_url}}
- 文本: 请分析这张封面

### [Bug6修复] 图片传入方式

Coze LLM节点支持多模态输入, 图片要用Image类型传入, 不能当文本填。
在Coze里配置节点6: 添加输入 -> 选Image类型 -> 值填 cover_url。
---

### 节点7 - LLM: 8维度爆款分析

类型: LLM

模型: DeepSeek / GPT-4o / Claude (纯文本即可)

系统提示词 (直接复制 viral_analysis_prompt.txt 的全部内容):

```
﻿你是一个短视频爆款分析师，专精于抖音平台的内容拆解与策略复盘。

请根据提供的素材（关键帧画面描述 + 结构化元数据），按以下八个维度逐一分析，输出结构化解析卡。

---

## 分析维度

### 1. 前3秒钩子
用了什么策略让用户停止滑动？钩子类型是什么（认知冲突/情绪共鸣/利益诱导/信息差/好奇/视觉冲击）？

### 2. 内容结构
视频分几个段落？每段的叙事功能是什么？

### 3. 目标受众
这个视频面向什么人群？年龄、兴趣、需求特征是什么？

### 4. 情绪与痛点
触发了哪种情绪？戳中了什么痛点？

### 5. 核心洞察
这个视频为什么会爆？最核心的驱动力是什么？一句话总结爆款原因。

### 6. 拍摄/剪辑手法
镜头运用、字幕设计、BGM、节奏等技术层面的具体亮点

### 7. 行动引导（CTA）
如何引导用户点赞/评论/收藏/关注？是软引导还是硬推销？

### 8. 出版社复用建议
这个视频的核心手法如何迁移到图书/出版行业的内容创作？给出具体可操作的建议。

---

## 要求
- 基于视频实际内容分析，不推断，不编造
- 每个维度2-4句，简洁直接
- 第8点必须给出出版社能直接参考的具体做法

---

## 输出格式

```
## 1. 前3秒钩子
- 钩子策略: ...
- 钩子类型: ...

## 2. 内容结构
- 段落划分: ...
- 叙事功能: ...

## 3. 目标受众
- 人群画像: ...
- 需求特征: ...

## 4. 情绪与痛点
- 触发情绪: ...
- 核心痛点: ...

## 5. 核心洞察
- 爆款原因: ...
- 核心驱动力: ...

## 6. 拍摄/剪辑手法
- 镜头: ...
- 字幕: ...
- BGM: ...
- 节奏: ...

## 7. 行动引导（CTA）
- 引导方式: ...
- CTA类型: ...

## 8. 出版社复用建议
- 可直接复用: ...
- 需适配调整: ...
- 避坑提醒: ...
```
```

用户消息 (根据是否有封面, 选不同的模板):

有封面时:
```
## 封面分析
{{节点6.output}}

---

{{节点5.user_message}}
```

无封面时 (跳过节点6):
```
{{节点5.user_message}}
```
---

### 节点8a - HTTP: 获取飞书 Access Token

类型: HTTP Request

```
方法: POST
URL: https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal
Headers:
  Content-Type: application/json
Body:
{
  "app_id": "{{env.FEISHU_APP_ID}}",
  "app_secret": "{{env.FEISHU_APP_SECRET}}"
}
```

从返回里取 tenant_access_token 字段。

### [Bug4修复] 飞书Token管理

Coze支持环境变量: 工作流 -> 变量管理 -> 添加 FEISHU_APP_ID 和 FEISHU_APP_SECRET
引用时用 {{env.FEISHU_APP_ID}}。每次工作流运行都重新获取Token, 不存在过期问题。

---

### 节点8b - Code: 判断 PUT / POST

类型: Code (Python)

输入: {{节点1.feishu_record_id}}

```python
def main(record_id: str) -> dict:
    if record_id and record_id.strip():
        return {"method": "PUT", "url_suffix": f"/records/{record_id}"}
    else:
        return {"method": "POST", "url_suffix": "/records"}
```

### [Bug5修复] record_id为空时的处理

飞书群聊Bot触发时没有record_id, 改用POST创建新行。
飞书表格webhook触发时自带record_id, 用PUT更新已有行。

---

### 节点8c - HTTP: 飞书多维表格回写

类型: HTTP Request

```
方法: {{节点8b.method}}
URL: https://open.feishu.cn/open-apis/bitable/v1/apps/
      {FEISHU_BASE_TOKEN}/tables/{FEISHU_TABLE_ID}{{节点8b.url_suffix}}
Headers:
  Authorization: Bearer {{节点8a.tenant_access_token}}
  Content-Type: application/json
Body:
{
  "fields": {
    "抖音链接": "{{节点1.douyin_url}}",
    "视频标题": "{{节点3.title}}",
    "作者": "{{节点3.author}}",
    "点赞数": {{节点3.digg}},
    "评论数": {{节点3.comment}},
    "分享数": {{节点3.share}},
    "收藏数": {{节点3.collect}},
    "标签": "{{节点3.tags}}",
    "BGM": "{{节点3.bgm}}",
    "封面分析": "{{节点6.output}}",
    "八维度分析报告": "{{节点7.output}}",
    "分析状态": "已完成"
  }
}
```

### [Bug8说明] Markdown渲染

八维度分析报告存的是原始Markdown, 飞书长文本字段不渲染Markdown。
用户点进单元格能看到完整内容。如需渲染, 可额外调飞书文档API创建独立文档。
---

### 节点9 - 结束

类型: End

正常输出:

| 变量 | 值 |
|------|-----|
| report | {{节点7.output}} |
| title | {{节点3.title}} |
| author | {{节点3.author}} |
| digg | {{节点3.digg}} |
| status | ok |

失败分支输出:

| 变量 | 值 |
|------|-----|
| status | 解析失败 |
| error | API返回异常 |

---

## 完整节点列表 (修正后)

```
1.开始
  |
2.HTTP: 抖音无水印解析
  | code!=200? -> 结束(失败)
  | code==200
3.Code: 拆字段 + 字段映射
  |
  | video_url为空? -> 跳到5
  | video_url有值
4.HTTP: 视频理解API
  |
5.Code: 拼装素材 (含截断+错误兜底)
  |
  | cover_url为空? -> 跳到7
  | cover_url有值
6.LLM: 封面视觉分析
  |
7.LLM: 8维度爆款分析
  |
8a.HTTP: 获取飞书Token
  |
8b.Code: 判断PUT/POST
  |
8c.HTTP: 飞书回写
  |
9.结束: ok
```

---

## Bug修复总结

| # | Bug | 严重度 | 修复方案 |
|---|-----|:---:|------|
| 1 | API失败全局崩溃 | 高 | 条件分支: code!=200 -> 结束 |
| 2 | 视频链接过期 | 中 | 节点5兜底: video_url为空时降级 |
| 3 | 视频理解失败静默 | 中 | 节点5检测error, 明确告知LLM |
| 4 | 飞书Token缺失 | 高 | 节点8a专门获取Token |
| 5 | record_id为空 | 中 | 节点8b判断PUT/POST |
| 6 | 封面图片传入方式 | 低 | 节点6用Coze多模态Image输入 |
| 7 | LLM Token超限 | 低 | 节点5截断关键帧总字数(3000) |
| 8 | Markdown渲染 | 低 | 存原始Markdown, 用户点开可读 |

---

## 操作步骤

| 步骤 | 做什么 | 时间 |
|------|--------|------|
| 1 | weiyiapi.com 注册拿 Key | 5min |
| 2 | tuputech.com 注册拿 Key | 5min |
| 3 | 飞书开放平台建应用 + 多维表格建字段 | 10min |
| 4 | Coze按本文档逐节点配置 | 15min |
| 5 | 测试: 贴一个抖音链接跑一遍 | 2min |
| | 总计 | ~37min |

---

## 关键注意事项

1. **字段名映射**: 不同无水印API返回字段名不同, 在节点3的g()里改key
2. **飞书表格字段名**: 节点8c的Body里字段名必须与多维表格建的字段名完全一致
3. **Coze变量**: FEISHU_APP_ID/FEISHU_APP_SECRET存在Coze工作流变量里, 不要硬编码
4. **图片传入**: 节点6的图片要用Image类型输入, 不是文本
5. **超时设置**: 节点4 (视频理解API) 超时设为90秒

## 一句话

**注册3个Key -> Coze配12个节点 -> 飞书贴链接出报告。零部署, 全网页操作。**