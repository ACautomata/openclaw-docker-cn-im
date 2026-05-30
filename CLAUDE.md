# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Docker image for [OpenClaw](https://github.com/openclaw/openclaw) — a multi-channel AI agent gateway — preconfigured for Chinese IM platforms (Feishu, DingTalk, QQ Bot, WeCom). All configuration is driven by environment variables and synced into `openclaw.json` at container startup.

## Build & Run

```bash
# Build image
docker compose build

# Start gateway
docker compose up -d

# View logs
docker compose logs -f openclaw-gateway

# Recreate after env changes (config sync only runs on startup)
docker compose up -d --force-recreate

# Installer tool container (one-off tasks like feishu plugin install)
docker compose --profile tools up -d openclaw-installer
docker exec -it openclaw-installer bash
```

## Architecture

**Two key files:**
- `Dockerfile` — image build: Node.js 22-slim + Python 3.12, global npm packages, pre-installed plugins
- `init.sh` (~2500 lines) — container entrypoint: a Python script that reads env vars, generates `openclaw.json`, syncs extensions, then starts `openclaw serve`

**Startup flow:**
1. `init.sh` runs as entrypoint (via `tini`)
2. Python section parses env vars → builds channel/model/plugin configs
3. Config written to `/home/node/.openclaw/openclaw.json`
4. Seed extensions copied from `/home/node/.openclaw-seed/extensions/` if volume is empty
5. `openclaw serve` started as `node` user

**Plugin system:**
- Pre-installed in Dockerfile under `/home/node/.openclaw/extensions/` (NapCat, DingTalk, QQBot, WeCom, LCM)
- Shipped as seed data, copied to named volume on first run
- `CHANNEL_INSTALLS` dict in init.sh (line ~384) maps channel IDs to npm specs and install paths
- Plugins are npm packages installed via `openclaw plugins install`

**Config sync system:**
- `SyncContext` class (init.sh ~line 1320) holds env state and orchestrates sync
- Each IM platform has normalize/sync/validate functions (e.g. `normalize_feishu_config`, `sync_feishu_channel`)
- Multi-account support for feishu, dingtalk, wecom, qqbot
- Model providers configured via `MODEL_1_*` through `MODEL_6_*` env vars

## Key Conventions

- Commit messages in Chinese with conventional commit prefixes: `feat:`, `fix:`, `docs:`
- Image version tracked in `version.txt`
- Environment variable template: `.env.example` (full) and `.env.minimal` (minimal)
- GitHub Actions workflow handles automated Docker image build and push
- Port 18789 is the gateway's default port

## Gotchas

- OpenClaw's built-in feishu extension requires `@larksuiteoapi/node-sdk` — must be in global npm install list
- `@larksuite/openclaw-lark-tools install` is commented out in Dockerfile because it requires interactive input — use the installer container instead
- After changing env vars, must `--force-recreate` the container (config sync only runs at startup)
- `NODE_PATH=/usr/local/lib/node_modules` is set so OpenClaw can find globally installed packages
