"""init.sh Python 配置生成逻辑的测试。"""

import json

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
        assert dp["apiKey"] == "test-key"
        assert dp["baseUrl"] == "https://api.example.com/v1"
        assert dp["api"] == "openai-completions"
        assert any(m["id"] == "gpt-4o" for m in dp["models"])

    def test_gateway_config(self, config_dir):
        cfg = run_sync(config_dir, {})
        gw = cfg["gateway"]
        assert gw["port"] == 18789
        assert gw["bind"] == "0.0.0.0"
        assert gw["auth"]["token"] == "test-ci-token"

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
        assert ch["appId"] == "cli_test_123"
        assert ch["appSecret"] == "test_secret_abc"
        assert "default" in ch["accounts"]
        assert ch["accounts"]["default"]["appId"] == "cli_test_123"
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
        assert providers["model2"]["apiKey"] == "key2"
        assert providers["google"]["apiKey"] == "key3"


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
    def test_lcm_enabled(self, config_dir):
        cfg = run_sync(config_dir, {
            "LCM_ENABLED": "true",
            "LCM_CONTEXT_THRESHOLD": "5000.0",
            "LCM_FRESH_TAIL_COUNT": "10",
        })
        assert cfg["plugins"]["entries"]["lossless-claw"]["enabled"] is True
        lcm_config = cfg["plugins"]["entries"]["lossless-claw"].get("config", {})
        assert lcm_config["contextThreshold"] == 5000.0
        assert lcm_config["freshTailCount"] == 10
        assert cfg["plugins"]["slots"]["contextEngine"] == "lossless-claw"

    def test_lcm_disabled(self, config_dir):
        cfg = run_sync(config_dir, {"LCM_ENABLED": "false"})
        assert cfg["plugins"]["entries"]["lossless-claw"]["enabled"] is False


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
        })
        channels = cfg["channels"]
        assert channels["feishu"]["enabled"] is True
        assert channels["dingtalk"]["enabled"] is True
        assert channels["qqbot"]["enabled"] is True
        assert channels["wecom"]["enabled"] is True
        assert channels["napcat"]["enabled"] is True
        assert channels["telegram"]["botToken"] == "111:token"
