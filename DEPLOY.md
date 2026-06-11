# 阿里云 FC 部署指南

## 价格

| 项目 | 数值 |
|------|------|
| 内存规格 | 2 GB |
| 每次分析耗时 | ~3 分钟 |
| 每次消耗 | ~360 CU-秒 |
| 免费额度 | 40 万 CU-秒/月 |
| 每月免费可分析 | ~1100 次 |
| 超出后 | ~0.018 元/次 |

正常用量下 **零费用**。

---

## 第1步: 构建 Docker 镜像

在你的项目目录下:

```bash
docker build -t douyin-analyzer .
```

镜像约 2-3 GB（含 Chromium + ffmpeg + Playwright），构建需要 5-10 分钟。

---

## 第2步: 本地测试

```bash
# 先确保 .env 里填好了 API Key
docker run -p 9000:9000 --env-file .env douyin-analyzer
```

验证:

```bash
curl http://localhost:9000/health
# 应返回: {"status": "ok", ...}
```

---

## 第3步: 推送到阿里云容器镜像服务 (ACR)

1. 打开 [cr.console.aliyun.com](https://cr.console.aliyun.com)
2. 创建个人实例（免费）
3. 创建命名空间（如 `douyin`）
4. 创建镜像仓库（如 `analyzer`）
5. 按页面提示登录 + 推送:

```bash
docker login --username=你的阿里云账号 registry.cn-hangzhou.aliyuncs.com
docker tag douyin-analyzer registry.cn-hangzhou.aliyuncs.com/douyin/analyzer:latest
docker push registry.cn-hangzhou.aliyuncs.com/douyin/analyzer:latest
```

---

## 第4步: 创建 FC 函数

1. 打开 [fc.console.aliyun.com](https://fc.console.aliyun.com)
2. 创建函数 → **使用容器镜像**
3. 选择刚才推送的镜像
4. 配置:

| 配置项 | 值 |
|--------|-----|
| 内存 | 2048 MB (2 GB) |
| 超时时间 | 600 秒 (10 分钟) |
| 实例并发度 | 1 |
| 监听端口 | 9000 |

5. 环境变量:

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `LLM_PROVIDER` | deepseek | LLM 提供商 |
| `LLM_API_KEY` | sk-xxx | DeepSeek API Key |
| `LLM_MODEL` | deepseek-chat | 模型名 |
| `VISION_PROVIDER` | ark | 视觉模型提供商 |
| `VISION_API_KEY` | ark-xxx | 火山引擎 Key |
| `VISION_MODEL` | doubao-seed-1-8-251228 | 豆包模型 |
| `FEISHU_BASE_TOKEN` | xxx | 飞书 Base Token |
| `FEISHU_TABLE_ID` | xxx | 飞书表格 ID |

6. 创建 HTTP 触发器:
   - 触发方式: HTTP
   - 认证方式: 无需认证（或按需设置）
   - 请求方法: GET, POST

7. 部署！

---

## 第5步: 连接飞书

部署后你会拿到一个公网 URL，类似:

```
https://xxx.cn-hangzhou.fc.aliyuncs.com/xxx
```

### 方式A: 飞书多维表格 Webhook

在飞书多维表格 → 自动化 → 新建触发器:
- 触发条件: 记录创建 / 字段修改
- 执行操作: Webhook
- URL: `https://你的FC地址/webhook`
- 请求体:
```json
{
  "url": "{{抖音链接字段}}",
  "record_id": "{{record_id}}"
}
```

### 方式B: 飞书群聊 Bot

在飞书开放平台创建 Bot → 消息事件 → 收到消息时:
- 提取消息中的抖音链接
- 调 FC 的 `/webhook` 接口
- 分析完成后，结果写回多维表格

---

## 第6步: 初始化飞书授权

首次使用需要登录 lark-cli。在 FC 控制台 → 函数详情 → 实例 → 登录终端:

```bash
/root/go/bin/cli auth login --domain base
# 扫码登录飞书
```

---

## 完成

飞书里贴抖音链接 → 自动触发 FC → Puppeteer 提取视频 → ffmpeg 抽帧 → 豆包描述画面 → DeepSeek 8维度分析 → 飞书表格回写。

一条链路，零维护。
