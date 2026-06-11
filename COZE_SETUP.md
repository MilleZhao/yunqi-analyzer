# Coze Bot 配置指南

## 架构概览

```
飞书 Bitable（待处理队列 新增记录）
    │
    ▼ 飞书自动化 → Webhook
Coze Bot（接收 webhook，提取 URL）
    │
    ▼ HTTP Request 节点
云电脑 API Server（异步处理管线）
    │
    ▼ 写入飞书
飞书 Bitable（爆款分析结果 表）
```

## 第一步：在 Coze 创建 Bot

1. 打开 https://www.coze.cn  → 点击「创建 Bot」
2. Bot 名称：`抖音爆款分析`（或自定义）
3. Bot 描述：`接收飞书 webhook，触发云电脑管线分析抖音视频`
4. 图标：随意选一个
5. 点击「确认」

## 第二步：配置 Webhook 触发器

1. 进入 Bot 编辑页 → 左侧「触发器」→ 添加「Webhook 触发器」
2. 点击「生成 URL」→ **复制 webhook URL，后续飞书自动化需要用到**
3. 输入变量定义（从 webhook body 中提取）：

```json
{
  "url": "$.url",
  "record_id": "$.record_id",
  "抖音链接": "$.抖音链接"
}
```

> 变量说明：Coze 用 JSONPath 从 webhook body 提取字段。飞书自动化发送的 JSON 中，`url` 存抖音链接，`record_id` 存飞书记录 ID。

## 第三步：添加 HTTP Request 节点

1. 左侧「节点」→ 拖入「HTTP 请求」节点
2. 配置：

| 配置项 | 值 |
|---|---|
| 请求方法 | POST |
| URL | `http://<云电脑IP>:8080/trigger` |
| Headers | `Content-Type: application/json` |
| Body | 见下方 |

**Body（JSON）：**
```json
{
  "url": "{{url 或 抖音链接}}",
  "record_id": "{{record_id}}"
}
```

> ⚠️ 注意：用的是 `/trigger` 端点（异步），不是 `/webhook`（同步）。管线跑一次 2-5 分钟，Coze HTTP 节点超时时间不够，所以用 fire-and-forget 模式。

3. 超时设置：30 秒（`/trigger` 立即返回，不需要长超时）

## 第四步：添加结束响应

1. 添加「文本回复」节点，内容：
```
✅ 分析任务已提交
视频链接：{{url}}
预计 3-5 分钟后可在飞书「爆款分析结果」表中查看。
```

2. 连线：HTTP Request（成功）→ 文本回复

## 第五步：发布 Bot

1. 点击右上角「发布」
2. 确认 webhook URL 不变

---

## 飞书自动化配置（第三步）

### 创建自动化规则

1. 打开飞书 Bitable（Base Token: `RlGBbQpxBalchssDFJbcuBjGnee`）
2. 进入「待处理队列」表
3. 右上角「自动化」→「新建自动化」
4. 触发器：**「新增记录时」**
5. 执行动作：**「发送 Webhook」**

### Webhook 配置

| 配置项 | 值 |
|---|---|
| Webhook URL | （Coze Bot 的 webhook URL） |
| 请求方法 | POST |
| Content-Type | application/json |

**Body 模板：**
```json
{
  "url": "{{抖音链接字段的值}}",
  "record_id": "{{记录ID}}"
}
```

> 字段名根据「待处理队列」表的实际列名调整。如果是「抖音链接」列，用 `{{抖音链接}}`。

### 更新记录状态

添加第二个执行动作：「更新记录」，将「状态」字段改为 `处理中`。

---

## 测试流程

1. 在飞书「待处理队列」表手动添加一条记录，填入抖音视频链接
2. 飞书自动化应触发 → 调用 Coze webhook
3. Coze Bot 收到请求 → HTTP 请求节点调用云电脑 `/trigger`
4. 云电脑开始处理（查看日志确认）
5. 3-5 分钟后检查飞书「爆款分析结果」表是否有新记录

---

## 常见问题

**Q: Coze HTTP 节点报超时？**
A: 确认用的是 `/trigger` 而非 `/webhook`。`/trigger` 是异步的，立即返回。

**Q: 云电脑 IP 变了怎么办？**
A: Coze 云电脑通常有固定内网 IP。如果使用公网 VPS，建议绑定域名。

**Q: 飞书自动化没触发？**
A: 检查自动化规则是否「已启用」，确认触发器条件正确（新增记录时 → 所有字段）。
