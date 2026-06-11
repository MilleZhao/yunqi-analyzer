# 飞书凭证获取指南

## 第一步：获取 App ID + App Secret

### 1. 打开飞书开放平台
浏览器打开：https://open.feishu.cn/app

如果没有账号，用飞书扫码登录。

### 2. 创建应用
点击右上角 **「创建企业自建应用」**

![创建应用](https://sf3-cn.feishucdn.com/obj/website-img/xxx)

- 应用名称：随便填，比如「爆款分析」
- 应用描述：随便填

### 3. 拿到凭证
创建完后，左侧菜单 → **「凭证与基础信息」**

你会看到：
```
App ID:     cli_a7xxxxxxxxxxxx
App Secret: xxxxxxxxxxxxxxxxxxxxxxxx
```
这就是需要的两个值。

### 4. 添加权限
左侧菜单 → **「权限管理」** → 搜索并添加：
- `base`（多维表格）— 全部勾上
- `drive`（云文档）— 勾 `drive:base:read_only` 即可

### 5. 发布应用
右上角 **「创建版本」** → 填写版本号（如 1.0.0）→ **「保存」** → **「申请线上发布」**

管理员审核通过后就能用了（你自己就是管理员的话，即时生效）。

---

## 第二步：获取 base_token

### 在飞书客户端
1. 打开你的多维表格（或新建一个空的）
2. 复制浏览器地址栏的 URL

```
https://xxxxxx.feishu.cn/base/BASCnNjMxsRxxxxxxxxx?table=tblxxxx
                            ^^^^^^^^^^^^^^^^^^^^^^^^
                            这就是 base_token
```

`BASC` 开头的那一串就是 base_token。

---

## 第三步：配置 CLI

拿到 App ID + App Secret 后，在终端运行：

```powershell
# 加载 CLI
$env:Path = "$env:LOCALAPPDATA\Programs\Go\go\bin;$env:USERPROFILE\go\bin;$env:Path"

# 开始配置
& "$env:USERPROFILE\go\bin\cli.exe" config init
```

交互式问答：
```
App ID: cli_a7xxxxxxxxxxxx        ← 粘贴你的 App ID
App Secret: xxxxxxxxxxxxxxxxxx    ← 粘贴你的 App Secret
```

然后它会输出一个验证链接，**复制到浏览器打开**，点授权。完成后再设 base_token：

```powershell
$env:FEISHU_BASE_TOKEN = "BASCnNjMxsRxxxxxxxxx"
```

验证一切正常：
```powershell
& "$env:USERPROFILE\go\bin\cli.exe" base table-list --base-token $env:FEISHU_BASE_TOKEN --json
```

能看到表列表就说明打通了。