# grok-reg-tool

[![开源协议：MIT](https://img.shields.io/badge/%E5%8D%8F%E8%AE%AE-MIT-green.svg)](LICENSE)
[![部署方式：Docker Compose](https://img.shields.io/badge/%E9%83%A8%E7%BD%B2-Docker%20Compose-blue.svg)](docker/docker-compose.yml)
[![Node.js 20+](https://img.shields.io/badge/Node.js-20+-339933.svg)](package.json)
[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-3776AB.svg)](register/requirements.txt)

`grok-reg-tool` 是一个可自部署的 Grok 注册机 Web 控制台，包含 React 仪表盘、Node.js API 服务、WebSocket 实时日志、内置 Python 自动化注册运行时，以及本地账号号池管理能力。

当前发布版已经把 Python 注册机源码放在项目内的 `register/` 目录中。Docker 镜像构建时会自动安装 Python、Chromium、Xvfb 和注册脚本依赖；部署者只需要拉取仓库、填写 `docker/.env`，然后执行 `docker compose up -d --build`。

> 本项目与 xAI、Grok、X 没有任何从属、授权或官方关联。请仅在合法、合规、获得许可的研究、学习或自托管实验环境中使用。请勿用于垃圾注册、滥用、撞库、绕过访问控制、干扰第三方服务，或任何违反法律法规和平台条款的行为。

## 功能特性

- 提供 Web 控制台，用于启动、停止和监控注册任务。
- 内置 Python 自动化入口 `register/runner.py`。
- Docker 构建阶段自动安装 `register/requirements.txt` 中的 Python 依赖。
- 支持配置自托管邮件后端，用于轮询验证码邮件。
- 支持本地账号记录、运行设置、日志和 SSO 输出持久化。
- 支持 HTTP 代理、浏览器代理、Chromium 路径、注册轮数和邮件后端参数。
- 默认使用 Docker Compose 部署，运行数据统一落在 `docker/data/`。
- 仓库已包含开源协议、GitHub Issue 模板、PR 模板和 Docker 配置。

## 搜索关键词

Grok 注册机、Grok 自动注册、Grok Web 控制台、Grok 账号号池、Grok SSO 管理、xAI 自动化、DrissionPage 自动化、Docker 自部署注册工具、Docker Compose WebUI、Python 自动化注册脚本、自托管自动化控制台。

## 环境要求

Docker 部署需要：

- Docker
- Docker Compose v2
- 一个可访问的邮件后端服务

本地开发需要：

- Node.js 20+
- npm
- Python 3.13+
- Chromium 或兼容浏览器

## Docker Compose 部署

克隆仓库：

```bash
git clone https://github.com/FengZi1221/grok-reg-tool.git
cd grok-reg-tool/docker
```

创建环境变量文件：

```bash
cp .env.example .env
```

编辑 `docker/.env`：

```env
WEB_PORT=6657
RUN_COUNT=10

MAIL_API_BASE=
MAIL_ADMIN_AUTH=
MAIL_DOMAIN=

HTTP_PROXY=
BROWSER_PROXY=
```

构建并启动：

```bash
docker compose up -d --build
```

打开 Web 控制台：

```text
http://你的服务器IP:6657
```

查看初始 Web 登录信息：

```bash
docker logs grok-reg-tool
```

首次登录后，请在 Web 控制台中修改默认用户名和密码。

## 镜像构建说明

Docker 镜像由 [docker/Dockerfile](docker/Dockerfile) 构建。

构建过程中会执行：

- 使用 Vite 构建 React 前端。
- 编译 TypeScript 服务端。
- 裁剪 Node.js 开发依赖。
- 使用 `python:3.13-slim-bookworm` 作为最终运行时基础镜像。
- 安装 Chromium、Xvfb、字体、证书和 `dumb-init`。
- 将项目内 `register/` 复制到容器内 `/app/register`。
- 执行 `python -m pip install -r /app/register/requirements.txt` 安装 Python 依赖。

容器默认参数：

| 变量 | 默认值 |
| --- | --- |
| `PORT` | `6657` |
| `BIND_HOST` | `0.0.0.0` |
| `DATA_DIR` | `/data` |
| `STATIC_ROOT` | `/app/out/renderer` |
| `PYTHON_PATH` | `/usr/local/bin/python3` |
| `REGISTER_DIR` | `/app/register` |
| `SSO_DIR` | `/data/sso` |
| `BROWSER_PATH` | `/usr/bin/chromium` |

## 运行数据

Docker Compose 默认只挂载一个持久化目录：

```yaml
volumes:
  - ./data:/data
```

常用路径：

| 用途 | 容器路径 | 宿主机路径 |
| --- | --- | --- |
| 应用配置和账号数据 | `/data` | `docker/data` |
| SSO 输出 | `/data/sso` | `docker/data/sso` |
| 内置注册脚本 | `/app/register` | 已打包进镜像 |
| Python 注册入口 | `/app/register/runner.py` | 已打包进镜像 |

请不要提交运行数据、SSO token、邮件凭据、代理密钥或生成的账号文件。

## 配置说明

Docker 用户可以在 `docker/.env` 中设置默认值。登录 Web 控制台后，大部分配置也可以在界面中修改。

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `WEB_PORT` | Docker Compose 暴露到宿主机的 Web 端口 | `6657` |
| `RUN_COUNT` | 单次运行的注册轮数 | `10` |
| `MAIL_API_BASE` | 邮件后端 API 根地址 | 空 |
| `MAIL_ADMIN_AUTH` | 邮件后端管理认证密钥或密码 | 空 |
| `MAIL_DOMAIN` | 生成邮箱地址使用的域名 | 空 |
| `HTTP_PROXY` | 后端 HTTP 请求使用的代理 | 空 |
| `BROWSER_PROXY` | 浏览器自动化使用的代理 | 空 |

## 本地开发

安装 Node.js 依赖：

```bash
npm install
```

构建前端和服务端：

```bash
npm run server:build
```

以开发模式运行服务端：

```bash
npm run server:dev
```

安装 Python 注册脚本依赖：

```bash
python -m pip install -r register/requirements.txt
```

直接运行 Python 注册入口：

```bash
python register/runner.py --count 1
```

## 项目结构

```text
grok-reg-tool/
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── entrypoint.sh
│   └── .env.example
├── register/
│   ├── runner.py
│   ├── DrissionPage_example.py
│   ├── email_register.py
│   ├── requirements.txt
│   └── turnstilePatch/
├── server/
│   └── src/
├── src/
│   ├── renderer/
│   └── shared/
├── package.json
└── README.md
```

## 常见问题

### Docker 首次构建较慢

镜像会安装 Chromium 和 Python 依赖，首次构建耗时会比较长。后续构建如果命中 Docker 层缓存，会快很多。

### Web 控制台可以打开，但注册任务无法正常运行

请检查：

- `MAIL_API_BASE`、`MAIL_ADMIN_AUTH` 和 `MAIL_DOMAIN`
- 代理配置是否正确
- `docker logs grok-reg-tool` 中的容器日志
- Web 控制台中的系统健康检查结果

### 浏览器自动化在自定义环境中失败

官方 Dockerfile 默认设置 `BROWSER_PATH=/usr/bin/chromium`，并在容器启动时自动启动 Xvfb。如果你修改了镜像或运行环境，请确认 Chromium 存在，并且当前进程有权限启动浏览器。

## 安全和隐私

仓库已默认忽略本地密钥和生成数据，包括：

- `.env`
- `docker/.env`
- `docker/data/`
- `register/config.json`
- `register/logs/`
- `register/sso/`
- `out/`
- `node_modules/`
- `server/dist/`

如果你把 Web 控制台暴露到公网，请设置强密码，尽量限制访问来源，并在任何凭据泄露后立即轮换邮件后端密钥和代理凭据。

## 负责任使用

本项目用于技术研究、自托管自动化实验，以及学习如何把 Docker、React、Node.js、Python 和 DrissionPage 组合成可由 Web 控制的自动化工作流。

你需要自行对使用方式负责。使用前请阅读相关平台的服务条款并遵守所在地法律法规。维护者不支持滥用、垃圾注册、绕过访问控制、干扰平台服务，或未经授权的大规模账号创建。

## 发行版

当前发行版：`v0.1.0`

GitHub 仓库：<https://github.com/FengZi1221/grok-reg-tool>

## 贡献

欢迎提交 Issue 和 Pull Request。

- 问题反馈请包含 Docker 日志、运行环境和复现步骤。
- 功能建议请说明使用场景和期望行为。
- 请不要提交密钥、真实 SSO token、密码、邮件凭据或个人账号数据。

## 开源协议

本项目基于 [MIT 开源协议](LICENSE) 开源。
