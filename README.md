# grok-reg-tool

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](docker/docker-compose.yml)
[![Node.js](https://img.shields.io/badge/Node.js-20+-339933.svg)](package.json)
[![Python](https://img.shields.io/badge/Python-3.13+-3776AB.svg)](register/requirements.txt)

`grok-reg-tool` is a self-hosted Grok registration Web console with Docker Compose deployment, a React dashboard, a Node.js API server, and an included DrissionPage Python automation runtime.

`grok-reg-tool` 是一个可自部署的 Grok 注册机 Web 控制台。当前发布版已经把 Python 注册机源码放在项目内的 `register/` 目录中，Docker 镜像构建时会自动安装 Python、Chromium、Xvfb 以及注册脚本依赖。部署者只需要拉取仓库、填写 `docker/.env`，然后执行 `docker compose up -d --build`。

> This project is not affiliated with xAI, Grok, or X. Use it only for lawful automation research, personal learning, and environments where you have permission. Do not use it for spam, abuse, credential stuffing, platform disruption, or any activity that violates applicable laws or service terms.

## What It Does

- Provides a Web UI for starting, stopping, and monitoring registration runs.
- Runs the included Python automation entrypoint `register/runner.py`.
- Installs Python dependencies from `register/requirements.txt` during Docker build.
- Integrates with a self-hosted mail backend for verification-code polling.
- Stores account records, settings, logs, and SSO output in a persistent Docker data directory.
- Supports HTTP proxy, browser proxy, Chromium path, run count, and mail backend settings.
- Includes GitHub-ready open-source metadata, issue templates, Docker configuration, and MIT license.

## SEO Keywords

Grok registration tool, Grok register WebUI, xAI automation dashboard, DrissionPage Docker automation, self-hosted registration console, Grok account pool manager, SSO token management, Docker Grok tool, Grok 注册机, Grok 自动注册, xAI 自动化, DrissionPage 自动化, Docker 自部署 Web 控制台。

## Requirements

For Docker deployment:

- Docker
- Docker Compose v2
- A reachable mail backend compatible with the project configuration

For local development:

- Node.js 20+
- npm
- Python 3.13+
- Chromium or a compatible browser

## Docker Compose Deployment

Clone the repository:

```bash
git clone https://github.com/FengZi1221/grok-reg-tool.git
cd grok-reg-tool/docker
```

Create an environment file:

```bash
cp .env.example .env
```

Edit `docker/.env`:

```env
WEB_PORT=6657
RUN_COUNT=10

MAIL_API_BASE=
MAIL_ADMIN_AUTH=
MAIL_DOMAIN=

HTTP_PROXY=
BROWSER_PROXY=
```

Build and start:

```bash
docker compose up -d --build
```

Open the Web UI:

```text
http://your-server-ip:6657
```

View the initial Web login information:

```bash
docker logs grok-reg-tool
```

After first login, change the default Web username and password in the UI.

## Build Details

The Docker image is built from `docker/Dockerfile`.

During build, the image:

- Builds the React renderer with Vite.
- Builds the TypeScript server.
- Prunes Node.js development dependencies.
- Uses `python:3.13-slim-bookworm` as the final runtime base.
- Installs Chromium, Xvfb, fonts, certificates, and `dumb-init`.
- Copies `register/` into `/app/register`.
- Installs Python dependencies with `python -m pip install -r /app/register/requirements.txt`.

Container defaults:

| Variable | Default |
| --- | --- |
| `PORT` | `6657` |
| `BIND_HOST` | `0.0.0.0` |
| `DATA_DIR` | `/data` |
| `STATIC_ROOT` | `/app/out/renderer` |
| `PYTHON_PATH` | `/usr/local/bin/python3` |
| `REGISTER_DIR` | `/app/register` |
| `SSO_DIR` | `/data/sso` |
| `BROWSER_PATH` | `/usr/bin/chromium` |

## Runtime Data

Docker Compose mounts one persistent directory:

```yaml
volumes:
  - ./data:/data
```

Important runtime paths:

| Purpose | Container Path | Host Path |
| --- | --- | --- |
| App config and account data | `/data` | `docker/data` |
| SSO output | `/data/sso` | `docker/data/sso` |
| Included register scripts | `/app/register` | baked into image |
| Python entrypoint | `/app/register/runner.py` | baked into image |

Do not commit runtime data, SSO tokens, mail credentials, proxy secrets, or generated account files.

## Configuration

Docker users can set defaults in `docker/.env`. Most values can also be changed from the Web UI after login.

| Variable | Description | Default |
| --- | --- | --- |
| `WEB_PORT` | Host port exposed by Docker Compose | `6657` |
| `RUN_COUNT` | Number of registration rounds per run | `10` |
| `MAIL_API_BASE` | Mail backend API base URL | empty |
| `MAIL_ADMIN_AUTH` | Mail backend admin auth token/password | empty |
| `MAIL_DOMAIN` | Mail domain used for generated addresses | empty |
| `HTTP_PROXY` | Proxy for backend HTTP requests | empty |
| `BROWSER_PROXY` | Proxy for browser automation | empty |

## Local Development

Install dependencies:

```bash
npm install
```

Build the Web UI and server:

```bash
npm run server:build
```

Run the server in development mode:

```bash
npm run server:dev
```

Install Python dependencies for local automation testing:

```bash
python -m pip install -r register/requirements.txt
```

Run the Python entrypoint directly:

```bash
python register/runner.py --count 1
```

## Project Structure

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

## Troubleshooting

### Docker build is slow

The image installs Chromium and Python dependencies, so the first build may take a while. Later builds are faster when Docker layer cache is available.

### Web UI starts but registration cannot run

Check:

- `MAIL_API_BASE`, `MAIL_ADMIN_AUTH`, and `MAIL_DOMAIN`
- proxy settings
- container logs with `docker logs grok-reg-tool`
- the system health panel in the Web UI

### Browser automation fails in a custom environment

The official Dockerfile sets `BROWSER_PATH=/usr/bin/chromium` and starts Xvfb automatically. If you change the image or runtime environment, verify that Chromium exists and the process has permission to launch it.

## Security and Privacy

The repository ignores local secrets and generated data, including:

- `.env`
- `docker/.env`
- `docker/data/`
- `register/config.json`
- `register/logs/`
- `register/sso/`
- `out/`
- `node_modules/`
- `server/dist/`

If you expose the Web UI on a public network, use a strong password, restrict access where possible, and rotate any leaked mail backend or proxy credentials immediately.

## Responsible Use

This project is published for technical research, self-hosted automation experiments, and learning how to combine Docker, React, Node.js, Python, and DrissionPage into a Web-controlled automation workflow.

You are responsible for how you run it. Review the terms of service of every platform involved and comply with local laws. The maintainer does not endorse abuse, spam, bypassing access controls, platform disruption, or unauthorized large-scale account creation.

## Release

Current release: `v0.1.0`

GitHub repository: <https://github.com/FengZi1221/grok-reg-tool>

## Contributing

Issues and pull requests are welcome.

- Bug reports should include Docker logs, environment details, and reproduction steps.
- Feature requests should describe the use case and expected behavior.
- Do not submit secrets, live SSO tokens, passwords, mail credentials, or personal account data.

## License

This project is released under the [MIT License](LICENSE).
