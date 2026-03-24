# 配置指南

本文聚焦 [`OpenClaw-Docker-CN-IM`](../README.md) 的核心配置项，包括模型、Gateway、工作空间、环境变量组织方式，以及与 [`openclaw.json.example`](../openclaw.json.example) 的对应关系。

## 配置文件关系

项目主要涉及以下几个配置入口：

| 文件 | 作用 |
| --- | --- |
| [`.env.example`](../.env.example) | 环境变量模板，复制为 `.env` 后使用 |
| [`docker-compose.yml`](../docker-compose.yml) | 把环境变量注入容器并定义卷、端口、服务 |
| [`openclaw.json.example`](../openclaw.json.example) | OpenClaw 配置结构示例，用于理解最终生成结果 |
| [`init.sh`](../init.sh) | 启动时读取环境变量并生成 / 修正实际配置 |

默认情况下，容器首次启动时会根据环境变量自动生成 `openclaw.json`。如果你已经手动维护该文件，建议同时关注 [`SYNC_MODEL_CONFIG`](../.env.example) 的行为。

---

## AI 模型配置

项目支持两类协议：

- `openai-completions`
- `openai-responses`
- `google-generative-ai`
- `anthropic-messages`

推荐先完成这一部分，再接入 IM 平台。

### 基础参数

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `MODEL_ID` | 模型名称，支持多个值，逗号分隔 | `model id` |
| `PRIMARY_MODEL` | 显式指定 [`agents.defaults.model.primary`](../openclaw.json.example) | 留空 |
| `IMAGE_MODEL_ID` | 图片模型名称，可单独指定 | 留空 |
| `BASE_URL` | Provider Base URL | `http://xxxxx/v1` |
| `API_KEY` | Provider API Key | `123456` |
| `API_PROTOCOL` | API 协议类型 | `openai-completions` |
| `CONTEXT_WINDOW` | 上下文窗口大小 | `200000` |
| `MAX_TOKENS` | 最大输出 token 数 | `8192` |

### 协议说明

| 协议类型 | 适用模型 | Base URL 习惯 | 说明 |
| --- | --- | --- | --- |
| `openai-completions` | OpenAI、Gemini 等 | 通常需要 `/v1` | 最常见接入方式 |
| `openai-responses` | OpenAI (Beta) | 通常需要 `/v1` | 适合 OpenAI 新版协议 |
| `google-generative-ai` | Gemini (Native) | 通常不需要 `/v1` | 适合 Google 原生协议 |
| `anthropic-messages` | Claude | 通常不需要 `/v1` | 适合 Claude 原生协议 |

### OpenAI 协议示例

```bash
MODEL_ID=gemini-3-flash-preview
BASE_URL=http://localhost:3000/v1
API_KEY=your-api-key
API_PROTOCOL=openai-completions
CONTEXT_WINDOW=1000000
MAX_TOKENS=8192
```

### Claude 协议示例

```bash
MODEL_ID=claude-sonnet-4-5
BASE_URL=http://localhost:3000
API_KEY=your-api-key
API_PROTOCOL=anthropic-messages
CONTEXT_WINDOW=200000
MAX_TOKENS=8192
```

### 默认 Provider 的名称

当你只配置第一组模型环境变量，也就是 `MODEL_ID`、`BASE_URL`、`API_KEY`、`API_PROTOCOL` 这一组时，项目生成到 `openclaw.json` 里的默认 Provider 名称固定为 `default`。

这意味着：

- 第一组模型配置会落到 `models.providers.default`
- 如果没有显式设置 `PRIMARY_MODEL`，默认主模型会引用 `default/<MODEL_ID 的第一个值>`
- 如果没有显式设置 `IMAGE_MODEL_ID`，默认图片模型也会回退到 `default/<MODEL_ID 的第一个值>`

例如：

```bash
MODEL_ID=gemini-3-flash-preview
```

最终默认引用通常会是：

- `default/gemini-3-flash-preview`

这也是为什么在配置 `PRIMARY_MODEL` 或 `IMAGE_MODEL_ID` 时，经常会看到 `default/...` 这种写法。

---

## 多 Provider 配置

如果需要同时接多个模型提供商，可以继续配置 `MODEL2_*`、`MODEL3_*` 等扩展项，具体环境变量定义见 [`.env.example`](../.env.example)。

### 示例：第二个 Provider 作为默认主模型

```bash
MODEL_ID=dashscope/qwen3.5-plus
MODEL2_NAME=aliyun
MODEL2_MODEL_ID=qwen-max,qwen3.5-plus,qwen-vl-max
PRIMARY_MODEL=aliyun/qwen3.5-plus
IMAGE_MODEL_ID=aliyun/qwen-vl-max
```

此时：

- `MODEL_ID` 仍会生成默认 Provider
- `MODEL2_*` 会生成第二个 Provider
- `PRIMARY_MODEL` 优先决定默认主模型
- `IMAGE_MODEL_ID` 优先决定默认图片模型

### 优先级

- 主模型：`PRIMARY_MODEL` → `MODEL_ID`
- 图片模型：`IMAGE_MODEL_ID` → `MODEL_ID`

这两个值都可以直接写完整引用，例如：

- `default/dashscope/qwen3.5-plus`
- `aliyun/qwen3.5-plus`
- `aliyun/qwen-vl-max`
- `model2/claude-sonnet-4-5`

---

## Gateway 配置

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `OPENCLAW_GATEWAY_TOKEN` | Gateway 访问令牌 | `123456` |
| `OPENCLAW_GATEWAY_BIND` | 绑定地址 | `lan` |
| `OPENCLAW_GATEWAY_PORT` | Gateway 端口 | `18789` |
| `OPENCLAW_BRIDGE_PORT` | Bridge 端口 | `18790` |
| `OPENCLAW_GATEWAY_MODE` | 运行模式 | `local` |
| `OPENCLAW_GATEWAY_ALLOWED_ORIGINS` | 允许的来源域 | `http://localhost` |
| `OPENCLAW_GATEWAY_ALLOW_INSECURE_AUTH` | 是否允许不安全认证 | `true` |
| `OPENCLAW_GATEWAY_DANGEROUSLY_DISABLE_DEVICE_AUTH` | 是否禁用设备认证 | `false` |
| `OPENCLAW_GATEWAY_AUTH_MODE` | 认证模式 | `token` |

这些配置最终会映射到 [`gateway`](../openclaw.json.example) 节点。

---

## 工作空间与数据目录

### 工作空间

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `WORKSPACE` | OpenClaw 工作空间目录 | `/home/node/.openclaw/workspace` |

### 数据目录挂载

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `OPENCLAW_DATA_DIR` | 宿主机挂载目录 | `~/.openclaw` |
| `OPENCLAW_RUN_USER` | 容器运行用户 UID:GID | `0:0` |

默认设计是：

1. 容器先以 root 启动
2. [`init.sh`](../init.sh) 尝试修复挂载目录权限
3. 再以更合适的用户运行 OpenClaw

如果你明确知道宿主机目录的 UID/GID，可以把 `OPENCLAW_RUN_USER` 改成例如 `1000:1000`。

---

## IM 渠道多账号 / 多机器人配置

本项目当前通过环境变量直接支持以下多账号结构：

- 飞书：`FEISHU_ACCOUNTS_JSON`
- 钉钉：`DINGTALK_ACCOUNTS_JSON`
- QQ 机器人：`QQBOT_BOTS_JSON`
- 企业微信：`WECOM_ACCOUNTS_JSON`

这些环境变量会把不同平台的账号信息同步到各自的 `channels.*` 节点中，例如：

- 飞书写入 `channels.feishu.accounts`
- 钉钉写入 `channels.dingtalk.accounts`
- QQ 机器人写入 `channels.qqbot.accounts`
- 企业微信写入 `channels.wecom`

如果你需要把某个平台的不同账号进一步路由到不同 OpenClaw Agent，建议直接手动维护宿主机上的 [`openclaw.json`](../openclaw.json.example)，并组合使用：

- `agents.list`：定义多个 OpenClaw Agent
- `bindings`：定义 `channel + accountId -> agentId` 路由规则
- 对应平台下的多账号配置：例如 `channels.feishu.accounts`、`channels.dingtalk.accounts`、`channels.qqbot.accounts` 或 `channels.wecom`

`bindings` 的典型写法如下：

```jsonc
"bindings": [
  {
    "type": "route",
    // 路由目标：这里写 OpenClaw agent 的 ID
    "agentId": "main",
    "match": {
      // 这里写具体渠道名称，例如 dingtalk / feishu / qqbot / wecom
      "channel": "your-channel",
      // 这里必须与对应 channels.<channel>.accounts（或渠道账号节点）下的 key 完全一致
      "accountId": "bot_1"
    }
  },
  {
    "type": "route",
    // 这里把 bot_2 路由到 growth-agent
    "agentId": "growth-agent",
    "match": {
      "channel": "your-channel",
      // 必须与对应渠道中 bot_2 这个账号 key 对应
      "accountId": "bot_2"
    }
  }
],
```

使用这类路由配置时，建议将 `SYNC_OPENCLAW_CONFIG=false`，避免启动时被环境变量同步覆盖手动维护的其它节点。

默认工具配置结构可参考 [`tools`](../openclaw.json.example) 节点。

## 插件与工具配置

| 参数 | 说明 |
| --- | --- |
| `OPENCLAW_PLUGINS_ENABLED` | 是否启用插件系统 |
| `OPENCLAW_TOOLS_JSON` | 自定义工具配置 JSON |

默认工具配置结构可参考 [`tools`](../openclaw.json.example) 节点。

---

## 与 `openclaw.json` 的关系

运行后生成的实际配置，通常会包含以下几个重要部分：

- `models.providers`
- `agents.defaults`
- `channels`
- `gateway`
- `plugins`
- `tools`

建议把 [`openclaw.json.example`](../openclaw.json.example) 当作“结构参考”，把 [`.env.example`](../.env.example) 当作“操作入口”。

---

## 修改环境变量后为什么不生效

容器启动时，只有在配置文件不存在时才会生成新的 `openclaw.json`。如果你修改了环境变量但发现没有生效，说明当前数据目录里已经存在旧配置。

### 方案一：删除配置文件后重启

```bash
rm ~/.openclaw/openclaw.json
docker compose restart
```

### 方案二：删除整个数据目录重新生成

```bash
rm -rf ~/.openclaw
docker compose up -d
```

更完整的故障排查见 [`docs/faq.md`](faq.md)。

## 下一步

- 快速部署与升级：[`docs/quick-start.md`](quick-start.md)
- 故障排查：[`docs/faq.md`](faq.md)
- AIClient-2-API：[`docs/aiclient-2-api.md`](aiclient-2-api.md)
- 项目总览：[`README.md`](../README.md)
