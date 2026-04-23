import json
import os
import subprocess
import sys
import unittest.mock
from pathlib import Path

import pytest

# 在导入提取的模块之前，mock subprocess.run 以避免调用 qmd
_original_run = subprocess.run


def _mock_run(cmd, *args, **kwargs):
    if isinstance(cmd, list) and any("qmd" in str(c) for c in cmd):
        return subprocess.CompletedProcess(cmd, 0, stdout=b"1.0.0\n", stderr=b"")
    return _original_run(cmd, *args, **kwargs)


subprocess.run = _mock_run

# 动态导入提取的模块
sys.path.insert(0, str(Path(__file__).resolve().parent))

# 触发模块提取（如果尚未提取）
module_path = Path(__file__).resolve().parent / "openclaw_config_module.py"
if not module_path.exists():
    from tests.extract_python import extract

    extract(
        Path(__file__).resolve().parent.parent / "init.sh",
        module_path,
    )

import openclaw_config_module  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_module_globals():
    """每个测试之间不共享模块级可变状态（当前模块无全局状态，预留）。"""
    yield


@pytest.fixture
def config_dir(tmp_path):
    """创建临时配置目录并写入骨架 openclaw.json，返回目录路径。"""
    config_file = tmp_path / "openclaw.json"
    config_file.write_text(
        json.dumps(
            {
                "meta": {"lastTouchedVersion": "2026.2.14"},
                "update": {"checkOnStart": False},
                "browser": {
                    "headless": True,
                    "noSandbox": True,
                    "defaultProfile": "openclaw",
                    "executablePath": "/usr/bin/chromium",
                },
                "models": {"mode": "merge", "providers": {"default": {"models": []}}},
                "agents": {
                    "defaults": {
                        "compaction": {"mode": "safeguard"},
                        "sandbox": {"mode": "off", "workspaceAccess": "none"},
                        "elevatedDefault": "full",
                        "maxConcurrent": 4,
                        "subagents": {"maxConcurrent": 8},
                    }
                },
                "messages": {
                    "ackReactionScope": "group-mentions",
                    "tts": {
                        "auto": "off",
                        "mode": "final",
                        "provider": "edge",
                        "providers": {
                            "edge": {
                                "voice": "zh-CN-XiaoxiaoNeural",
                                "lang": "zh-CN",
                                "outputFormat": "ogg-24khz-16bit-mono-opus",
                                "pitch": "+0Hz",
                                "rate": "+0%",
                                "volume": "+0%",
                                "timeoutMs": 30000,
                            }
                        },
                    },
                },
                "commands": {"native": "auto", "nativeSkills": "auto"},
                "tools": {
                    "profile": "full",
                    "sessions": {"visibility": "all"},
                    "fs": {"workspaceOnly": True},
                },
                "channels": {},
                "plugins": {"entries": {}, "installs": {}},
                "memory": {
                    "backend": "qmd",
                    "citations": "auto",
                    "qmd": {
                        "includeDefaultMemory": True,
                        "sessions": {"enabled": True},
                        "limits": {"timeoutMs": 8000, "maxResults": 16},
                        "update": {"onBoot": True, "interval": "5m", "debounceMs": 15000},
                        "command": "/usr/local/bin/qmd",
                        "paths": [
                            {
                                "name": "workspace",
                                "path": "/home/node/.openclaw/workspace",
                                "pattern": "**/*.md",
                            }
                        ],
                    },
                },
                "gateway": {},
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return tmp_path


def run_sync(config_dir, env_overrides):
    """设置环境变量并运行 sync()，返回生成的 config dict。"""
    config_file = str(config_dir / "openclaw.json")

    base_env = {
        "CONFIG_FILE": config_file,
        "OPENCLAW_HOME": str(config_dir),
        "SYNC_OPENCLAW_CONFIG": "true",
        "SYNC_MODEL_CONFIG": "true",
        "MODEL_ID": "gpt-4o",
        "BASE_URL": "https://api.example.com/v1",
        "API_KEY": "test-key",
        "API_PROTOCOL": "openai-completions",
        "CONTEXT_WINDOW": "128000",
        "MAX_TOKENS": "4096",
        "OPENCLAW_GATEWAY_TOKEN": "test-ci-token",
        "OPENCLAW_GATEWAY_PORT": "18789",
        "OPENCLAW_GATEWAY_BIND": "0.0.0.0",
        "AGENT_REACH_ENABLED": "false",
    }
    base_env.update(env_overrides)

    old_env = os.environ.copy()
    os.environ.update(base_env)
    try:
        openclaw_config_module.sync()
    finally:
        os.environ.clear()
        os.environ.update(old_env)

    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)
