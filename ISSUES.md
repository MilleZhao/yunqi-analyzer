# 踩坑日志 - 阿里云FC部署

## 目标
将抖音爆款分析管线部署到阿里云FC，飞书贴链接自动出报告。不依赖Coze。

## 尝试过的路径

### 1. 全在Coze跑 (已放弃)
- 原因: Coze代码节点无ffmpeg/Puppeteer，无法提取视频和关键帧
- 结论: 不适用此场景

### 2. ACR在线构建 (已放弃)
- Docker Hub拉不到 (GFW) -> 改用DaoCloud镜像 -> 解决
- .dockerignore中文注释导致ASCII解析错误 -> 纯英文注释 -> 解决
- libasound2在Ubuntu24.04已改名libasound2t64 -> 解决
- GitHub代码源clone超时 (内网拉GitHub不稳) -> 放弃
- Gitee代码源ACR不支持直接绑定 -> 放弃

### 3. GitHub Actions构建+推送ACR (已放弃)
- Actions runner下载外部action超时 -> 改用纯shell命令 -> 解决
- docker login ACR失败 (GitHub境外到ACR上海不通) -> 放弃
- lark-cli下载卡住 -> 从Dockerfile移除 -> 解决

### 4. 本地Docker构建 (当前卡点)
- WSL未正确安装 -> wsl --install (需管理员权限)
- 需重启电脑后生效

## 当前状态
- Dockerfile: 干净可用，无lark-cli，Python+Node+ffmpeg+Chromium完整
- .github/workflows/build.yml: 存在但ACR登录失败
- 本地: WSL已启用但需重启
- 代码已推送到GitHub和Gitee

## 下一步
1. 重启电脑使WSL生效
2. 打开Docker Desktop
3. 本地构建: docker build -t douyin-analyzer .
4. 本地验证: docker run -p 9000:9000 --env-file .env douyin-analyzer
5. docker login crpi-hhhd1ym0vn8x5l6u.cn-shanghai.personal.cr.aliyuncs.com
6. docker push
7. 阿里云FC创建函数，选容器镜像

## 技术备忘

### Dockerfile关键修复
- 基础镜像: docker.m.daocloud.io/library/ubuntu:24.04 (国内可拉)
- apt源: mirrors.aliyun.com
- npm源: registry.npmmirror.com
- libasound2 -> libasound2t64 (Ubuntu24.04包名变更)
- --no-sandbox自动检测 (Docker内root运行Chromium必需)
- .dockerignore必须纯ASCII
- lark-cli移除 (改用飞书HTTP API)

### ACR凭证
- Registry: crpi-hhhd1ym0vn8x5l6u.cn-shanghai.personal.cr.aliyuncs.com
- Namespace: mille / Repo: videoanalysis
- 用户名: 阿里云账号 密码: ACR固定密码

### FC配置
- 内存: 2048MB 超时: 600s 端口: 9000
- 环境变量: LLM_API_KEY, VISION_API_KEY, FEISHU_BASE_TOKEN等
