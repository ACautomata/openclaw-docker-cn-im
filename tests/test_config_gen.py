"""init.sh Python 配置生成逻辑的测试。"""

import json
import os
import types

import pytest

from conftest import run_sync


class TestMinimalConfig:
    """仅提供基础模型和 gateway 配置。"""

    def test_valid_json(self, config_dir):
        cfg = run_sync(config_dir, {})
        assert isinstance(cfg, dict)

    def test_default_provider(self, config_dir):
        cfg = run_sync(config_dir, {})
        dp = cfg["models"]["providers"]["default"]
        assert dp["apiKey"] == "${API_KEY}"
        assert dp["baseUrl"] == "https://api.example.com/v1"
        assert dp["api"] == "openai-completions"
        assert any(m["id"] == "gpt-4o" for m in dp["models"])

    def test_gateway_config(self, config_dir):
        cfg = run_sync(config_dir, {})
        gw = cfg["gateway"]
        assert gw["port"] == 18789
        assert gw["bind"] == "lan"
        assert gw["auth"]["token"] == "${OPENCLAW_GATEWAY_TOKEN}"

    def test_no_channels_enabled(self, config_dir):
        cfg = run_sync(config_dir, {})
        entries = cfg["plugins"]["entries"]
        for ch in ["feishu", "dingtalk", "qqbot", "openclaw-qqbot", "napcat", "wecom", "telegram"]:
            if ch in entries:
                assert entries[ch].get("enabled") is not True, f"{ch} 不应启用"


class TestFeishu:
    def test_single_account(self, config_dir):
        cfg = run_sync(config_dir, {
            "FEISHU_APP_ID": "cli_test_123",
            "FEISHU_APP_SECRET": "test_secret_abc",
        })
        ch = cfg["channels"]["feishu"]
        assert ch["enabled"] is True
        assert ch["appId"] == "${FEISHU_APP_ID}"
        assert ch["appSecret"] == "${FEISHU_APP_SECRET}"
        assert "default" in ch["accounts"]
        assert ch["accounts"]["default"]["appId"] == "${FEISHU_APP_ID}"
        assert cfg["plugins"]["entries"]["feishu"]["enabled"] is True

    def test_multi_account(self, config_dir):
        accounts_json = json.dumps({
            "default": {"appId": "cli_aaa", "appSecret": "s_aaa", "name": "Bot 1"},
            "bot2": {"appId": "cli_bbb", "appSecret": "s_bbb", "name": "Bot 2"},
        })
        cfg = run_sync(config_dir, {
            "FEISHU_ACCOUNTS_JSON": accounts_json,
        })
        ch = cfg["channels"]["feishu"]
        accounts = ch.get("accounts", {})
        assert len(accounts) >= 2


class TestDingTalk:
    def test_single_account(self, config_dir):
        cfg = run_sync(config_dir, {
            "DINGTALK_CLIENT_ID": "ding_test_id",
            "DINGTALK_CLIENT_SECRET": "ding_test_secret",
        })
        ch = cfg["channels"]["dingtalk"]
        assert ch["enabled"] is True
        assert ch["clientId"] == "ding_test_id"
        assert ch["clientSecret"] == "ding_test_secret"
        assert cfg["plugins"]["entries"]["dingtalk"]["enabled"] is True

    def test_with_streaming_options(self, config_dir):
        cfg = run_sync(config_dir, {
            "DINGTALK_CLIENT_ID": "ding_test_id",
            "DINGTALK_CLIENT_SECRET": "ding_test_secret",
            "DINGTALK_CARD_STREAMING_MODE": "answer",
            "DINGTALK_MESSAGE_TYPE": "markdown",
        })
        ch = cfg["channels"]["dingtalk"]
        assert ch["cardStreamingMode"] == "answer"
        assert ch["messageType"] == "markdown"


class TestQQBot:
    def test_single_account(self, config_dir):
        cfg = run_sync(config_dir, {
            "QQBOT_APP_ID": "111111111",
            "QQBOT_CLIENT_SECRET": "test_qq_secret",
        })
        ch = cfg["channels"]["qqbot"]
        assert ch["enabled"] is True
        assert ch["appId"] == "111111111"
        assert cfg["plugins"]["entries"]["openclaw-qqbot"]["enabled"] is True


class TestWeCom:
    def test_single_account(self, config_dir):
        cfg = run_sync(config_dir, {
            "WECOM_BOT_ID": "test_bot_id",
            "WECOM_SECRET": "test_wecom_secret",
        })
        ch = cfg["channels"]["wecom"]
        assert ch["enabled"] is True
        assert ch["defaultAccount"] == "default"
        assert ch["default"]["botId"] == "test_bot_id"
        assert ch["default"]["secret"] == "test_wecom_secret"
        assert cfg["plugins"]["entries"]["wecom"]["enabled"] is True


class TestNapCat:
    def test_basic(self, config_dir):
        cfg = run_sync(config_dir, {
            "NAPCAT_REVERSE_WS_PORT": "3001",
            "NAPCAT_ACCESS_TOKEN": "test_nc_token",
            "NAPCAT_ADMINS": "12345,67890",
        })
        ch = cfg["channels"]["napcat"]
        assert ch["enabled"] is True
        assert ch["reverseWsPort"] == 3001
        assert ch["accessToken"] == "test_nc_token"
        assert ch["admins"] == [12345, 67890]
        assert cfg["plugins"]["entries"]["napcat"]["enabled"] is True


class TestTelegram:
    def test_basic(self, config_dir):
        cfg = run_sync(config_dir, {
            "TELEGRAM_BOT_TOKEN": "123456:test_token",
        })
        ch = cfg["channels"]["telegram"]
        assert ch["botToken"] == "123456:test_token"
        assert "streaming" in ch


class TestMultiProvider:
    def test_multiple_providers(self, config_dir):
        cfg = run_sync(config_dir, {
            "MODEL2_API_KEY": "key2",
            "MODEL2_BASE_URL": "https://api2.example.com/v1",
            "MODEL2_MODEL_ID": "claude-3-opus",
            "MODEL3_API_KEY": "key3",
            "MODEL3_BASE_URL": "https://api3.example.com/v1",
            "MODEL3_MODEL_ID": "gemini-pro",
            "MODEL3_NAME": "google",
        })
        providers = cfg["models"]["providers"]
        assert "default" in providers
        assert "model2" in providers
        assert "google" in providers
        assert providers["model2"]["apiKey"] == "${MODEL2_API_KEY}"
        assert providers["google"]["apiKey"] == "${MODEL3_API_KEY}"


class TestSyncControl:
    def test_sync_disabled(self, config_dir):
        cfg = run_sync(config_dir, {"SYNC_OPENCLAW_CONFIG": "false"})
        # 骨架中 gateway 是空 dict，sync 跳过后应保持空
        assert cfg["gateway"] == {}

    def test_model_sync_disabled(self, config_dir):
        cfg = run_sync(config_dir, {"SYNC_MODEL_CONFIG": "false"})
        providers = cfg["models"]["providers"]
        # sync 跳过时 providers 应只有骨架中的 default
        assert "default" in providers
        # default 的 models 应仍为空列表（骨架值）
        assert providers["default"]["models"] == []


class TestLCM:
    def test_lcm_enabled_with_defaults(self, config_dir):
        cfg = run_sync(config_dir, {"LCM_ENABLED": "true"})
        assert cfg["plugins"]["entries"]["lossless-claw"]["enabled"] is True
        assert cfg["plugins"]["slots"]["contextEngine"] == "lossless-claw"

    def test_lcm_disabled(self, config_dir):
        cfg = run_sync(config_dir, {"LCM_ENABLED": "false"})
        assert cfg["plugins"]["entries"]["lossless-claw"]["enabled"] is False
        assert "contextEngine" not in cfg["plugins"].get("slots", {})

    def test_lcm_numeric_params(self, config_dir):
        cfg = run_sync(config_dir, {
            "LCM_ENABLED": "true",
            "LCM_CONTEXT_THRESHOLD": "0.85",
            "LCM_FRESH_TAIL_COUNT": "128",
            "LCM_INCREMENTAL_MAX_DEPTH": "2",
            "LCM_LEAF_CHUNK_TOKENS": "40000",
            "LCM_NEW_SESSION_RETAIN_DEPTH": "3",
            "LCM_LEAF_TARGET_TOKENS": "1500",
            "LCM_CONDENSED_TARGET_TOKENS": "2500",
            "LCM_MAX_EXPAND_TOKENS": "8000",
            "LCM_LEAF_MIN_FANOUT": "12",
            "LCM_CONDENSED_MIN_FANOUT": "6",
            "LCM_CONDENSED_MIN_FANOUT_HARD": "3",
            "LCM_LARGE_FILE_TOKEN_THRESHOLD": "50000",
            "LCM_DELEGATION_TIMEOUT_MS": "180000",
            "LCM_SUMMARY_TIMEOUT_MS": "90000",
            "LCM_CACHE_TTL_SECONDS": "600",
        })
        c = cfg["plugins"]["entries"]["lossless-claw"]["config"]
        assert c["contextThreshold"] == 0.85
        assert c["freshTailCount"] == 128
        assert c["incrementalMaxDepth"] == 2
        assert c["leafChunkTokens"] == 40000
        assert c["newSessionRetainDepth"] == 3
        assert c["leafTargetTokens"] == 1500
        assert c["condensedTargetTokens"] == 2500
        assert c["maxExpandTokens"] == 8000
        assert c["leafMinFanout"] == 12
        assert c["condensedMinFanout"] == 6
        assert c["condensedMinFanoutHard"] == 3
        assert c["largeFileThresholdTokens"] == 50000
        assert c["delegationTimeoutMs"] == 180000
        assert c["summaryTimeoutMs"] == 90000
        assert c["cacheAwareCompaction"]["cacheTTLSeconds"] == 600

    def test_lcm_string_params(self, config_dir):
        cfg = run_sync(config_dir, {
            "LCM_ENABLED": "true",
            "LCM_SUMMARY_MODEL": "openai/gpt-4o-mini",
            "LCM_SUMMARY_PROVIDER": "openai",
            "LCM_SUMMARY_BASE_URL": "https://api.custom.com/v1",
            "LCM_EXPANSION_MODEL": "anthropic/claude-haiku-4-5",
            "LCM_EXPANSION_PROVIDER": "anthropic",
            "LCM_DATABASE_PATH": "/data/lcm.db",
            "LCM_LARGE_FILE_SUMMARY_MODEL": "deepseek/deepseek-chat",
            "LCM_LARGE_FILE_SUMMARY_PROVIDER": "deepseek",
        })
        c = cfg["plugins"]["entries"]["lossless-claw"]["config"]
        assert c["summaryModel"] == "openai/gpt-4o-mini"
        assert c["summaryProvider"] == "openai"
        assert "summaryBaseUrl" not in c  # LCM reads LCM_SUMMARY_BASE_URL directly from env, not plugin config
        assert c["expansionModel"] == "anthropic/claude-haiku-4-5"
        assert c["expansionProvider"] == "anthropic"
        assert c["dbPath"] == "/data/lcm.db"
        assert c["largeFileSummaryModel"] == "deepseek/deepseek-chat"
        assert c["largeFileSummaryProvider"] == "deepseek"

    def test_lcm_bool_params(self, config_dir):
        cfg = run_sync(config_dir, {
            "LCM_ENABLED": "true",
            "LCM_SKIP_STATELESS_SESSIONS": "true",
            "LCM_PRUNE_HEARTBEAT_OK": "true",
            "LCM_TRANSCRIPT_GC_ENABLED": "true",
        })
        c = cfg["plugins"]["entries"]["lossless-claw"]["config"]
        assert c["skipStatelessSessions"] is True
        assert c["pruneHeartbeatOk"] is True
        assert c["transcriptGcEnabled"] is True

    def test_lcm_csv_params(self, config_dir):
        cfg = run_sync(config_dir, {
            "LCM_ENABLED": "true",
            "LCM_IGNORE_SESSION_PATTERNS": "agent:*:cron:**,agent:main:subagent:**",
            "LCM_STATELESS_SESSION_PATTERNS": "agent:*:subagent:**",
        })
        c = cfg["plugins"]["entries"]["lossless-claw"]["config"]
        assert c["ignoreSessionPatterns"] == ["agent:*:cron:**", "agent:main:subagent:**"]
        assert c["statelessSessionPatterns"] == ["agent:*:subagent:**"]

    def test_lcm_proactive_compaction_mode(self, config_dir):
        cfg = run_sync(config_dir, {
            "LCM_ENABLED": "true",
            "LCM_PROACTIVE_THRESHOLD_COMPACTION_MODE": "inline",
        })
        c = cfg["plugins"]["entries"]["lossless-claw"]["config"]
        assert c["proactiveThresholdCompactionMode"] == "inline"

    def test_lcm_empty_env_has_recommended_defaults(self, config_dir):
        cfg = run_sync(config_dir, {"LCM_ENABLED": "true"})
        lcm_entry = cfg["plugins"]["entries"]["lossless-claw"]
        assert lcm_entry["enabled"] is True
        c = lcm_entry["config"]
        assert c["freshTailCount"] == 64
        assert c["incrementalMaxDepth"] == 1
        assert c["contextThreshold"] == 0.75
        assert c["newSessionRetainDepth"] == 2

    def test_lcm_invalid_number_raises(self, config_dir):
        with pytest.raises(SystemExit):
            run_sync(config_dir, {
                "LCM_ENABLED": "true",
                "LCM_FRESH_TAIL_COUNT": "not-a-number",
            })


class TestAllChannels:
    """所有渠道同时启用。"""

    def test_all_enabled(self, config_dir):
        cfg = run_sync(config_dir, {
            "FEISHU_APP_ID": "cli_test",
            "FEISHU_APP_SECRET": "s_test",
            "DINGTALK_CLIENT_ID": "ding_id",
            "DINGTALK_CLIENT_SECRET": "ding_s",
            "QQBOT_APP_ID": "222222",
            "QQBOT_CLIENT_SECRET": "qq_s",
            "WECOM_BOT_ID": "wc_bot",
            "WECOM_SECRET": "wc_s",
            "NAPCAT_REVERSE_WS_PORT": "3001",
            "TELEGRAM_BOT_TOKEN": "111:token",
            "DISCORD_BOT_TOKEN": "discord-token",
        })
        channels = cfg["channels"]
        assert channels["feishu"]["enabled"] is True
        assert channels["dingtalk"]["enabled"] is True
        assert channels["qqbot"]["enabled"] is True
        assert channels["wecom"]["enabled"] is True
        assert channels["napcat"]["enabled"] is True
        assert channels["telegram"]["botToken"] == "111:token"
        assert channels["discord"]["enabled"] is True
        assert channels["discord"]["token"]["id"] == "DISCORD_BOT_TOKEN"


def _make_normalize_ctx(installs, entries):
    """创建 normalize_install_paths 所需的最小 ctx 对象。"""
    import openclaw_config_module as mod
    ctx = types.SimpleNamespace()
    ctx.installs = installs
    ctx.entries = entries
    ctx.plugins = {"allow": list(installs.keys())}
    return ctx


def _create_npm_layout(base_dir, packages):
    """在 base_dir 下创建模拟的 npm/node_modules 目录结构。

    packages: list of (scope, name) tuples, e.g. [('@openclaw', 'discord'), (None, 'some-pkg')]
    """
    nm_dir = os.path.join(base_dir, "npm", "node_modules")
    os.makedirs(nm_dir, exist_ok=True)
    for scope, name in packages:
        if scope:
            pkg_dir = os.path.join(nm_dir, scope, name)
        else:
            pkg_dir = os.path.join(nm_dir, name)
        os.makedirs(pkg_dir, exist_ok=True)
        # 写入 package.json 以便验证这是有效目录
        with open(os.path.join(pkg_dir, "package.json"), "w") as f:
            json.dump({"name": f"{scope}/{name}" if scope else name}, f)
    return nm_dir


class TestNormalizeInstallPaths:
    """测试 normalize_install_paths 对 extensions/ 和 npm/node_modules/ 的扫描。"""

    def test_npm_scoped_package_corrected(self, config_dir):
        """npm scoped 包（@openclaw/discord）在 npm/node_modules/ 中找到时，installPath 应被校正。"""
        import openclaw_config_module as mod

        _create_npm_layout(str(config_dir), [
            ("@openclaw", "discord"),
            ("@openclaw", "feishu"),
            ("@martian-engineering", "lossless-claw"),
        ])

        ctx = _make_normalize_ctx(
            installs={
                "discord": {"source": "npm", "spec": "@openclaw/discord", "installPath": f"{config_dir}/extensions/discord"},
                "feishu": {"source": "npm", "spec": "@openclaw/feishu", "installPath": f"{config_dir}/extensions/feishu"},
                "lossless-claw": {"source": "npm", "spec": "@martian-engineering/lossless-claw", "installPath": f"{config_dir}/extensions/lossless-claw"},
            },
            entries={
                "discord": {"enabled": True},
                "feishu": {"enabled": True},
                "lossless-claw": {"enabled": True},
            },
        )

        mod.normalize_install_paths(ctx, openclaw_home=str(config_dir))

        expected_discord = f"{config_dir}/npm/node_modules/@openclaw/discord"
        assert ctx.installs["discord"]["installPath"] == expected_discord
        assert ctx.installs["feishu"]["installPath"] == f"{config_dir}/npm/node_modules/@openclaw/feishu"
        assert ctx.installs["lossless-claw"]["installPath"] == f"{config_dir}/npm/node_modules/@martian-engineering/lossless-claw"
        # 应保持启用
        assert ctx.entries["discord"]["enabled"] is True
        assert ctx.entries["feishu"]["enabled"] is True
        assert ctx.entries["lossless-claw"]["enabled"] is True

    def test_extensions_dir_found_unchanged(self, config_dir):
        """extensions/ 中已有插件目录时，installPath 不应改变。"""
        import openclaw_config_module as mod

        ext_dir = os.path.join(str(config_dir), "extensions", "napcat")
        os.makedirs(ext_dir, exist_ok=True)

        original_path = f"{config_dir}/extensions/napcat"
        ctx = _make_normalize_ctx(
            installs={
                "napcat": {"source": "path", "installPath": original_path},
            },
            entries={"napcat": {"enabled": True}},
        )

        mod.normalize_install_paths(ctx, openclaw_home=str(config_dir))

        assert ctx.installs["napcat"]["installPath"] == original_path

    def test_plugin_not_found_disabled(self, config_dir):
        """插件在 extensions/ 和 npm/ 中都找不到时，应被禁用。"""
        import openclaw_config_module as mod

        # 创建一个不相关的 extensions 子目录，避免函数因空目录提前返回
        os.makedirs(os.path.join(str(config_dir), "extensions", "other-plugin"), exist_ok=True)

        ctx = _make_normalize_ctx(
            installs={
                "unknown-plugin": {"source": "npm", "spec": "@nonexistent/plugin", "installPath": f"{config_dir}/extensions/unknown-plugin"},
            },
            entries={"unknown-plugin": {"enabled": True}},
        )

        mod.normalize_install_paths(ctx, openclaw_home=str(config_dir))

        assert ctx.entries["unknown-plugin"]["enabled"] is False

    def test_spec_name_matching(self, config_dir):
        """插件 ID 与目录名不同时，通过 spec 包名匹配（如 dingtalk → @soimy/dingtalk）。"""
        import openclaw_config_module as mod

        _create_npm_layout(str(config_dir), [
            ("@soimy", "dingtalk"),
            ("@sunnoy", "wecom"),
            ("@tencent-connect", "openclaw-qqbot"),
        ])

        ctx = _make_normalize_ctx(
            installs={
                "dingtalk": {"source": "npm", "spec": "@soimy/dingtalk", "installPath": f"{config_dir}/extensions/dingtalk"},
                "wecom": {"source": "npm", "spec": "@sunnoy/wecom", "installPath": f"{config_dir}/extensions/wecom"},
                "openclaw-qqbot": {"source": "path", "spec": "@tencent-connect/openclaw-qqbot", "installPath": f"{config_dir}/extensions/openclaw-qqbot"},
            },
            entries={
                "dingtalk": {"enabled": True},
                "wecom": {"enabled": True},
                "openclaw-qqbot": {"enabled": True},
            },
        )

        mod.normalize_install_paths(ctx, openclaw_home=str(config_dir))

        assert ctx.installs["dingtalk"]["installPath"] == f"{config_dir}/npm/node_modules/@soimy/dingtalk"
        assert ctx.installs["wecom"]["installPath"] == f"{config_dir}/npm/node_modules/@sunnoy/wecom"
        assert ctx.installs["openclaw-qqbot"]["installPath"] == f"{config_dir}/npm/node_modules/@tencent-connect/openclaw-qqbot"

    def test_mixed_extensions_and_npm(self, config_dir):
        """napcat 在 extensions/ 中，其余在 npm/ 中，混合场景。"""
        import openclaw_config_module as mod

        os.makedirs(os.path.join(str(config_dir), "extensions", "napcat"), exist_ok=True)
        _create_npm_layout(str(config_dir), [
            ("@openclaw", "discord"),
        ])

        ctx = _make_normalize_ctx(
            installs={
                "napcat": {"source": "path", "installPath": f"{config_dir}/extensions/napcat"},
                "discord": {"source": "npm", "spec": "@openclaw/discord", "installPath": f"{config_dir}/extensions/discord"},
            },
            entries={
                "napcat": {"enabled": True},
                "discord": {"enabled": True},
            },
        )

        mod.normalize_install_paths(ctx, openclaw_home=str(config_dir))

        assert ctx.installs["napcat"]["installPath"] == f"{config_dir}/extensions/napcat"
        assert ctx.installs["discord"]["installPath"] == f"{config_dir}/npm/node_modules/@openclaw/discord"

    def test_empty_dirs_skips(self, config_dir):
        """extensions/ 和 npm/ 都为空时，函数应正常跳过，不改变任何状态。"""
        import openclaw_config_module as mod

        os.makedirs(os.path.join(str(config_dir), "extensions"), exist_ok=True)

        ctx = _make_normalize_ctx(
            installs={
                "discord": {"source": "npm", "spec": "@openclaw/discord", "installPath": f"{config_dir}/extensions/discord"},
            },
            entries={"discord": {"enabled": True}},
        )

        mod.normalize_install_paths(ctx, openclaw_home=str(config_dir))

        # 目录为空时函数跳过，状态不变
        assert ctx.entries["discord"]["enabled"] is True

    def test_allow_list_filtered(self, config_dir):
        """plugins.allow 中不存在的插件 ID 应被移除（需要有至少一个目录触发处理）。"""
        import openclaw_config_module as mod

        # 创建一个 extensions 子目录以触发主处理逻辑
        os.makedirs(os.path.join(str(config_dir), "extensions", "some-plugin"), exist_ok=True)

        ctx = _make_normalize_ctx(
            installs={},
            entries={},
        )
        ctx.plugins["allow"] = ["nonexistent-plugin", "another-missing"]

        mod.normalize_install_paths(ctx, openclaw_home=str(config_dir))

        assert ctx.plugins["allow"] == []
