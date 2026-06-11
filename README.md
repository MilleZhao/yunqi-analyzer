# 爆款视频分析工具

一键输入抖音视频链接，自动提取视频、关键帧分析、LLM 多维度拆解，生成结构化爆款分析报告，并自动写入飞书多维表格。

## 功能

- **视频提取** — 自动下载抖音视频、音频、封面、字幕
- **关键帧分析** — 视觉模型描述每一帧画面内容
- **LLM 爆款拆解** — 8 维度深度分析（前3秒钩子、内容结构、目标受众、情绪痛点、核心洞察、拍摄手法、CTA、出版社复用建议）
- **飞书自动入库** — 分析结果自动写入飞书多维表格，附分析报告附件
- **Web 操作面板** — 本地浏览器打开 `website/analyzer.html`，粘贴链接即可使用

## 快速开始

### 1. 安装依赖

```bash
# Python 依赖
pip install -r requirements.txt

# Node.js 依赖（视频提取用 Puppeteer）
npm install
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

需要配置两个 API：
| 用途 | 推荐 | 说明 |
|------|------|------|
| 文本分析 LLM | DeepSeek | 撰写 8 维度分析报告 |
| 视觉分析 | 火山引擎 Ark（豆包） | 描述关键帧画面 |
| 飞书多维表格 | 飞书开放平台 | 可选，分析结果自动归档 |

### 3. 启动服务

```bash
python api_server.py --port 8080
```

### 4. 打开面板

浏览器打开 `website/analyzer.html`，粘贴抖音链接，点击「一键分析」。

## 飞书多维表格配置（可选）

1. 在飞书开放平台创建一个 Base，获取 `BASE_TOKEN`
2. 在 Base 中创建表格，获取 `TABLE_ID`
3. 配置 `.env`：
   ```
   FEISHU_BASE_TOKEN=你的BaseToken
   FEISHU_TABLE_ID=你的TableId
   ```
4. 安装并登录 `lark-cli`（飞书命令行工具）

分析完成后，数据会自动写入飞书表格，分析报告作为附件上传。

## 管线流程

```
抖音链接 → extract_single.js（提取视频/音频/字幕/元数据）
         → extract_keyframes.py（提取关键帧图片）
         → describe_frames.py（视觉模型描述帧画面）
         → llm_analyze.py（LLM 8维度深度分析）
         → write_to_feishu.py（飞书多维表格归档）
```

每一步都有独立的脚本，可以单独调用。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/pipeline` | 完整管线分析（同步等待） |
| POST | `/trigger` | 异步触发分析 |
| GET | `/files/{path}` | 下载提取的素材文件 |

## 技术栈

- **后端**: Python 3.10+（HTTP Server + 管线编排）
- **视频提取**: Node.js + Puppeteer
- **文本分析**: DeepSeek / OpenAI 兼容 API
- **视觉分析**: 火山引擎 Ark / OpenAI Vision
- **数据归档**: 飞书多维表格 + lark-cli
- **前端**: 纯 HTML/CSS/JS（零框架依赖）

## License

MIT
