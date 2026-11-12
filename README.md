# Invoice Scanner

私人使用的账单扫描与结构化工具。上传账单图片 → PaddleOCR 逐页识别 → Claude 一次解析 → 结构化账单 JSON，浏览器查看结果。

---

## 功能

- 浏览器上传（手机可直接调起相机，或从相册多选）
- 每页保留完整 OCR 结果：文字、置信度、四边形 bbox、边界坐标
- Claude 解析供应商、日期、金额、VAT、商品明细，并输出字段关联关系（可追溯到具体 OCR item）
- OCR 与 Claude 分两步落盘，任一步失败可单独重试，不覆盖已成功的结果
- 刷新页面不会重复消耗 Claude token
- 列表页支持单条删除和清空全部
- 支持通过 mkcert 自签证书在局域网内以 HTTPS 访问，可安装为 PWA

不支持：编辑、确认、导出、校验、异步队列、数据库、离线。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11 + FastAPI + Uvicorn |
| 前端 | React 18 + TypeScript + Vite 5 |
| OCR | PaddleOCR 2.8.1 + paddlepaddle 2.6.2（CPU） |
| LLM | Claude Haiku 5.5（Anthropic SDK 2.8.0） |
| 存储 | 文件系统 |
| 运行环境 | Docker 容器 `python:3.11.0`，Node.js 22（nvm 安装） |

---

## 环境要求

**宿主机只需两样**：

- Docker Desktop（Windows / macOS）或 Docker Engine（Linux）
- VS Code + [Dev Containers 扩展](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

不需要在宿主机装 Python、Node、PaddleOCR。所有依赖都在容器里。

---

## 快速开始（推荐：VS Code Dev Container）

### 1. 准备宿主机

安装 Docker 和 VS Code + Dev Containers 扩展。

### 2. 克隆仓库并打开

```bash
git clone git@github.com:kevinprotoss/invoice-scanner.git
cd invoice-scanner
code .
```

### 3. 进入 Dev Container

VS Code 右下角弹出「Reopen in Container」→ 点击。

或：`Ctrl/Cmd+Shift+P` → `Dev Containers: Reopen in Container`。

首次构建约 5–10 分钟（PaddleOCR 依赖较大），之后秒开。

容器就绪后，当前目录自动是 `/workspace`。

### 4. 准备 `.env`

```bash
cp .env.example .env
```

编辑 `.env`，至少填这三项：

| 变量 | 生成方式 |
|---|---|
| `APP_PASSWORD_HASH` | `python scripts/make_password_hash.py`（输入密码，复制输出整行） |
| `APP_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ANTHROPIC_API_KEY` | 从 [Anthropic Console](https://console.anthropic.com/) 获取 |

**`APP_DATA_DIR` 在 devcontainer 里保持 `./data`**，此时数据落在 `/workspace/data`（对应宿主机项目根的 `data/`）。

### 5. 启动

打开两个终端。

终端 1（后端）：

```bash
cd backend
python run.py
```

期望日志：`Uvicorn running on http://0.0.0.0:8000`。

终端 2（前端）：

```bash
cd frontend
npm run dev
```

期望日志：`VITE v5.x.x ready in xxx ms`，地址 `http://localhost:5173`。

### 6. 访问

浏览器打开 <http://localhost:5173>，输入密码登录。

---

## 其他运行方式

### 方式 A：生产镜像（Docker 单容器，端口映射到宿主机）

构建：

```bash
docker build -t invoice-scanner:latest .
```

准备 `.env`：

```dotenv
APP_COOKIE_SECURE=0
APP_DATA_DIR=/data
```

启动：

```bash
docker run -d \
  --name invoice-scanner \
  -p 8000:8000 \
  --env-file .env \
  -v "$(pwd)/data:/data" \
  --restart unless-stopped \
  invoice-scanner:latest
```

访问 `http://localhost:8000`。

### 方式 B：生产镜像 + HTTPS

需要先准备证书（见「HTTPS 部署」一节），然后：

```dotenv
APP_COOKIE_SECURE=1
APP_DATA_DIR=/data
SSL_CERTFILE=/certs/localhost.pem
SSL_KEYFILE=/certs/localhost-key.pem
```

```bash
docker run -d \
  --name invoice-scanner \
  -p 443:8000 \
  --env-file .env \
  -v "$(pwd)/data:/data" \
  -v "$(pwd)/certs:/certs:ro" \
  --restart unless-stopped \
  invoice-scanner:latest
```

访问 `https://<host-ip>`（不带端口，443 是默认端口）。

---

## 生成密钥

### 密码哈希

```bash
python scripts/make_password_hash.py
```

输入密码，脚本输出一行 `pbkdf2_sha256$200000$...$...`，复制到 `.env` 的 `APP_PASSWORD_HASH`。

**不要**用 `python -c "...$..."` 生成——shell 会展开 `$` 导致哈希损坏。

### 签名密钥

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

复制到 `.env` 的 `APP_SECRET_KEY`。

---

## HTTPS 部署（局域网）

用于在局域网内通过 HTTPS 访问，可安装 PWA。

### 1. 生成证书

在容器内用 mkcert 生成一份本地 CA 和服务器证书。

```bash
docker run --rm -it -v "$(pwd)/certs:/certs" python:3.11.0 bash
```

容器内执行：

```bash
sed -i 's|deb.debian.org|archive.debian.org|g; s|security.debian.org|archive.debian.org|g' /etc/apt/sources.list
apt-get -o Acquire::Check-Valid-Until=false update
apt-get install -y --no-install-recommends ca-certificates libnss3-tools

curl -fsSL -o /usr/local/bin/mkcert \
  https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-amd64
chmod +x /usr/local/bin/mkcert

export CAROOT=/certs
mkcert -install
mkcert \
  -cert-file /certs/localhost.pem \
  -key-file  /certs/localhost-key.pem \
  localhost 127.0.0.1 ::1 192.168.178.104

exit
```

**把 `192.168.178.104` 换成部署主机的局域网 IP**。可以加多个 IP。

生成后项目根 `certs/` 下应有：

```
rootCA.pem             ← 公钥证书，分发到各客户端
rootCA-key.pem         ← 根私钥，只留宿主机，永不外传
localhost.pem          ← 服务器证书
localhost-key.pem      ← 服务器私钥
```

### 2. 客户端信任 CA

**Windows**（浏览器）：

```powershell
certutil -addstore -user Root .\certs\rootCA.pem
```

**Android**：

1. 把 `rootCA.pem` 传到手机
2. 设置 → 安全 → 加密与凭据 → 安装证书 → CA 证书 → 选择 `rootCA.pem`
3. 系统会警告"您的数据将不再是私密的"——这是 Android 对所有用户 CA 的标准提示。本项目的 CA 私钥只在你手上，不会带来第三方解密风险，可以放心安装

**iPhone / iPad**：

1. 用 Safari 下载 `rootCA.pem`，允许下载描述文件
2. 设置 → 通用 → VPN 与设备管理 → 安装 `mkcert` 描述文件
3. **设置 → 通用 → 关于本机 → 证书信任设置 → 打开 `mkcert` 开关**（必须做，否则无效）

### 3. 启动

见「方式 B：生产镜像 + HTTPS」。

---

## 目录结构

```
invoice-scanner/
├── .devcontainer/            开发容器配置（VS Code Dev Containers）
├── .env.example              环境变量模板
├── Dockerfile                生产镜像（多阶段）
├── README.md
├── backend/                  FastAPI 应用
│   ├── requirements.txt
│   ├── run.py
│   └── app/
├── frontend/                 React 应用
├── ocr/                      PaddleOCR 封装
│   └── paddle_runner.py
├── scripts/
│   ├── make_password_hash.py
│   ├── verify_password.py
│   └── ocr_debug.py
├── certs/                    TLS 证书（不进 git）
└── data/                     运行时数据（不进 git）
```

---

## 数据落盘

```
data/invoices/<YYYY>/<INV-YYYYMMDD-NNN>/
  document_id.txt               本次上传组的 UUID
  original/
    page_001.jpg                原始图片，永不修改
  ocr/
    page_001_ocr.json           单页 OCR，落盘后永不修改
    combined_ocr.json           存在 = OCR 就绪
  result/
    claude_raw.txt              Claude 原始响应，先于 invoice.json 写入
    invoice.json                存在 = 全部完成
```

---

## API

所有 `/api/invoices*` 需要登录 cookie。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/logout` | 登出 |
| GET | `/api/auth/me` | 认证状态 |
| POST | `/api/invoices` | 上传图片 + OCR |
| POST | `/api/invoices/{id}/images` | 追加图片 |
| POST | `/api/invoices/{id}/retry` | 重跑 OCR（幂等） |
| POST | `/api/invoices/{id}/process` | 调 Claude（幂等） |
| GET | `/api/invoices` | 列表 |
| GET | `/api/invoices/{id}` | 详情 |
| GET | `/api/invoices/{id}/result` | 结构化账单 |
| GET | `/api/invoices/{id}/raw` | Claude 原始响应 |
| GET | `/api/invoices/{id}/ocr` | 合并 OCR |
| GET | `/api/invoices/{id}/images` | 图片元数据 |
| GET | `/api/invoices/{id}/images/{page}` | 图片二进制 |
| DELETE | `/api/invoices/{id}` | 删除单条 |
| DELETE | `/api/invoices` | 清空全部 |

---

## 测试

```bash
# 健康检查
curl http://localhost:8000/api/health

# 登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password":"你的密码"}' \
  -c cookies.txt

# 上传
curl -b cookies.txt -X POST http://localhost:8000/api/invoices \
  -F "files=@/path/to/receipt.jpg"

# 触发 Claude
curl -b cookies.txt -X POST http://localhost:8000/api/invoices/INV-.../process
```

---

## 常见问题

| 问题 | 原因 / 解决 |
|---|---|
| `wrong version number` | Vite 代理目标写了 `https://` 但后端跑 HTTP，改成 `http://localhost:8000` |
| 密码正确但登录失败 | 哈希被 shell 破坏，用 `scripts/make_password_hash.py` 重新生成 |
| 详情页卡片只占左半边 | `styles.css` 里 `.card` 不应有 `max-width`，420px 只作用于 `.center .card` |
| Claude 返回 500 `schema validation failed` | `models/invoice.py` 里 `FieldRelationship.value` 必须是 `Any` |
| `f-string expression part cannot include a backslash` | Python 3.11 限制，把 `"\r" in x` 先算成变量再放进 f-string |
| 数据落到 `backend/data/` | `APP_DATA_DIR` 默认值应为绝对路径，基于 `config.py` 位置推算 |
| PaddleOCR 首次请求慢 | 约 10 秒初始化，属正常 |
| `ImportError: ...libz` | 需要 `LD_PRELOAD=/lib/x86_64-linux-gnu/libz.so.1`，Docker / devcontainer 已内置 |
| 手机能打开但 PWA 安装失败 | 检查 HTTPS 是否启用、客户端 CA 是否已信任 |
| iOS PWA 内无法拍照 | 确认 iOS 16+，或去掉 `capture` 属性让系统弹菜单 |

---

## 开发约定

- 所有 OCR 原始字段（`id / text / confidence / bbox / x_min / y_min / x_max / y_max`）不得增删
- 所有 JSON 写入使用原子写（`.tmp` + `replace`）
- 所有 Claude 调用经过 `services/llm_service.py`，其他模块不直接 `from anthropic import ...`
- 所有金额字段使用字符串（`"11.88"`），不用浮点数
- 前端使用 hash 路由，不引入 `react-router-dom`

---

## 许可

MIT License, 详见 [LICENSE](./LICENSE)