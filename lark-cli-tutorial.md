# Lark CLI 教程 — 飞书多维表格操作指南

## 已安装

| 组件 | 路径 | 版本 |
|---|---|---|
| Go | `%LOCALAPPDATA%\Programs\Go\go\bin` | 1.25.2 |
| lark-cli | `%USERPROFILE%\go\bin\cli.exe` | v1.0.50 |

## 一、获取凭证

### 方式 A：企业自建应用（推荐）

1. 打开 [飞书开放平台](https://open.feishu.cn/app)
2. 创建企业自建应用 → 获取 **App ID** 和 **App Secret**
3. 添加权限（至少勾选）：
   - `base`（多维表格）
   - `drive`（云文档）
4. 发布应用 → 管理员审核通过

### 方式 B：个人 access token（快速测试）

飞书网页版 → 头像 → 设置 → 开发者后台 → 创建 token

---

## 二、登录认证

```powershell
# 设置环境（每次新终端需执行）
$env:Path = "$env:LOCALAPPDATA\Programs\Go\go\bin;$env:USERPROFILE\go\bin;$env:Path"

# 交互式登录（浏览器扫码）
cli auth login --domain base

# 只申请推荐权限（无需管理员审批）
cli auth login --domain base --recommend

# 查看当前登录状态
cli auth status

# 退出
cli auth logout
```

---

## 三、多维表格核心操作

### 获取 base_token 和 table_id

每个多维表格都有一个 `base_token`（URL 里的那串字符），里面的每个表有 `table_id`。

```
飞书URL: https://xxx.feishu.cn/base/BASCxxxxxxxxxx?table=tblYYYYYYYY
                                  ^^^^^^^^^^^^        ^^^^^^^^^^^^
                                  base_token          table_id
```

### 列出所有表

```powershell
cli base table-list --base-token BASCxxxxxxxxxx
```

### 查看字段

```powershell
cli base field-list --base-token BASCxxxxxxxxxx --table-id tblYYYYYYYY
```

### 读取记录

```powershell
# 读取前100条
cli base record-list --base-token BASCxxxxxxxxxx --table-id tblYYYYYYYY --page-size 100

# JSON格式输出
cli base record-list --base-token BASCxxxxxxxxxx --table-id tblYYYYYYYY --json

# 搜索特定记录
cli base record-search --base-token BASCxxxxxxxxxx --table-id tblYYYYYYYY --search "关键词"
```

### 创建记录

```powershell
# 单条创建
cli base record-upsert --base-token BASCxxxxxxxxxx --table-id tblYYYYYYYY --data '{"fields":{"标题":"xxx","状态":"待处理"}}'

# 批量创建
cli base record-batch-create --base-token BASCxxxxxxxxxx --table-id tblYYYYYYYY --data '{"records":[{"fields":{"标题":"A","状态":"待处理"}},{"fields":{"标题":"B","状态":"进行中"}}]}'
```

### 更新记录

```powershell
# 单条更新
cli base record-upsert --base-token BASCxxxxxxxxxx --table-id tblYYYYYYYY --data '{"fields":{"状态":"已完成"},"record_id":"recXXXX"}'

# 批量更新
cli base record-batch-update --base-token BASCxxxxxxxxxx --table-id tblYYYYYYYY --data '{"records":[{"fields":{"状态":"已完成"},"record_id":"recXXXX"}]}'
```

### 删除记录

```powershell
cli base record-delete --base-token BASCxxxxxxxxxx --table-id tblYYYYYYYY --record-ids "recXXXX,recYYYY"
```

### 创建表和字段

```powershell
# 创建表
cli base table-create --base-token BASCxxxxxxxxxx --name "爆款分析结果" --fields '[{"field_name":"视频链接","type":1},{"field_name":"分析报告","type":1},{"field_name":"收藏点赞比","type":2}]'

# 添加字段到已有表
cli base field-create --base-token BASCxxxxxxxxxx --table-id tblYYYYYYYY --field-name "分析结论" --type 1
```

**常用字段类型**：1=文本, 2=数字, 3=单选, 4=多选, 5=日期, 7=复选框, 17=链接, 21=附件

---

## 四、高级查询（JSON DSL）

```powershell
cli base data-query --base-token BASCxxxxxxxxxx --table-id tblYYYYYYYY --data '{
  "filter": {
    "conjunction": "and",
    "conditions": [
      {"field_name": "状态", "operator": "is", "value": ["待处理"]},
      {"field_name": "点赞数", "operator": "isGreater", "value": [10000]}
    ]
  },
  "sort": [{"field_name": "收藏点赞比", "desc": true}],
  "aggregation": {
    "groups": [{"field_name": "标签", "type": "count"}]
  }
}'
```

---

## 五、Codex 集成思路

### 场景 1：分析结果自动写入多维表格

```
用户: 分析这条视频 https://www.douyin.com/video/xxx

Codex:
  1. 跑 run_pipeline.py 提取+分析
  2. 读 viral_analysis.md 取关键数据
  3. cli base record-create → 写入飞书表格
```

### 场景 2：从多维表格批量读取待分析链接

```
用户: 批量分析表格里所有待处理的视频

Codex:
  1. cli base record-list → 获取"状态=待处理"的记录
  2. 遍历每条记录的视频链接
  3. 逐条分析
  4. cli base record-update → 更新状态为"已完成"
```

### 场景 3：定时巡检

```
Codex:
  1. cli base record-search → 搜索本周新增视频
  2. 对比历史数据，找出数据异常的爆款
  3. 写分析报告并@相关人员
```

---

## 六、快捷别名（建议加到 PowerShell Profile）

```powershell
# 加到 $PROFILE
function lark { & "$env:USERPROFILE\go\bin\cli.exe" @args }
function lark-auth { & "$env:USERPROFILE\go\bin\cli.exe" auth login --domain base --recommend }

# 使用
lark base table-list --base-token BASCxxx
lark-auth
```

---

## 七、常用参数速查

| 参数 | 说明 |
|---|---|
| `--base-token` | 多维表格的 token（URL里 BASC 开头的那串） |
| `--table-id` | 表的 ID（URL里 tbl 开头） |
| `--field-id / --field-name` | 字段 ID 或字段名 |
| `--record-ids` | 记录 ID，逗号分隔 |
| `--page-size` | 每页条数，默认 100 |
| `--json` | 输出结构化 JSON |
| `--data` | 请求体，JSON 格式 |
| `--search` | 搜索关键词 |