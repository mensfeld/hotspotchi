"""Tests for config loading across the application."""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from hotspotchi.characters import SPECIAL_SSIDS
from hotspotchi.config import HotSpotchiConfig, MacMode, SsidMode, load_config, save_config


class TestLoadConfig:
    """Tests for the load_config function."""

    def test_load_config_from_file(self, temp_dir):
        """load_config should load settings from YAML file."""
        config_path = temp_dir / "config.yaml"
        config_data = {
            "wifi_interface": "wlan1",
            "concurrent_mode": True,
            "ap_interface": "ap0",
            "mac_mode": "random",
            "web_port": 9000,
        }
        with open(config_path, "w") as f:
            yaml.safe_dump(config_data, f)

        config = load_config(config_path)

        assert config.wifi_interface == "wlan1"
        assert config.concurrent_mode is True
        assert config.ap_interface == "ap0"
        assert config.mac_mode == MacMode.RANDOM
        assert config.web_port == 9000

    def test_load_config_missing_file(self):
        """load_config should return defaults when file doesn't exist."""
        config = load_config(Path("/nonexistent/config.yaml"))

        assert config.wifi_interface == "wlan0"
        assert config.concurrent_mode is False
        assert config.mac_mode == MacMode.DAILY_RANDOM

    def test_load_config_none_path(self):
        """load_config should return defaults when path is None."""
        config = load_config(None)

        assert config.wifi_interface == "wlan0"
        assert config.concurrent_mode is False

    def test_load_config_preserves_all_fields(self, temp_dir):
        """load_config should preserve all config fields from file."""
        config_path = temp_dir / "config.yaml"
        config_data = {
            "wifi_interface": "wlan1",
            "concurrent_mode": True,
            "ap_interface": "ap0",
            "ssid_mode": "special",
            "default_ssid": "MySSID",
            "special_ssid_index": 5,
            "mac_mode": "cycle",
            "fixed_character_index": 10,
            "include_special_ssids": False,
            "wifi_password": "testpass123",
            "ap_ip": "10.0.0.1",
            "web_host": "127.0.0.1",
            "web_port": 8888,
        }
        with open(config_path, "w") as f:
            yaml.safe_dump(config_data, f)

        config = load_config(config_path)

        assert config.wifi_interface == "wlan1"
        assert config.concurrent_mode is True
        assert config.ap_interface == "ap0"
        assert config.ssid_mode == SsidMode.SPECIAL
        assert config.default_ssid == "MySSID"
        assert config.special_ssid_index == 5
        assert config.mac_mode == MacMode.CYCLE
        assert config.fixed_character_index == 10
        assert config.include_special_ssids is False
        assert config.wifi_password == "testpass123"
        assert config.ap_ip == "10.0.0.1"
        assert config.web_host == "127.0.0.1"
        assert config.web_port == 8888


class TestConfigWithOverrides:
    """Tests for config override patterns used across the application."""

    def test_model_dump_preserves_all_fields(self):
        """model_dump() should include all config fields."""
        config = HotSpotchiConfig(
            wifi_interface="wlan1",
            concurrent_mode=True,
            mac_mode=MacMode.RANDOM,
        )

        dumped = config.model_dump()

        assert dumped["wifi_interface"] == "wlan1"
        assert dumped["concurrent_mode"] is True
        assert dumped["mac_mode"] == MacMode.RANDOM
        # Verify defaults are also included
        assert "ap_interface" in dumped
        assert "web_port" in dumped
        assert "ssid_mode" in dumped

    def test_override_preserves_other_fields(self):
        """Creating new config with overrides should preserve other fields."""
        original = HotSpotchiConfig(
            wifi_interface="wlan1",
            concurrent_mode=True,
            mac_mode=MacMode.RANDOM,
            web_port=9000,
        )

        # Override only mac_mode
        new_config = HotSpotchiConfig(**{**original.model_dump(), "mac_mode": MacMode.FIXED})

        # Changed field
        assert new_config.mac_mode == MacMode.FIXED
        # Preserved fields
        assert new_config.wifi_interface == "wlan1"
        assert new_config.concurrent_mode is True
        assert new_config.web_port == 9000

    def test_multiple_overrides(self):
        """Multiple overrides should all be applied."""
        original = HotSpotchiConfig(
            concurrent_mode=True,
            mac_mode=MacMode.RANDOM,
        )

        overrides = {
            "mac_mode": MacMode.FIXED,
            "fixed_character_index": 42,
            "ssid_mode": SsidMode.SPECIAL,
        }

        new_config = HotSpotchiConfig(**{**original.model_dump(), **overrides})

        assert new_config.mac_mode == MacMode.FIXED
        assert new_config.fixed_character_index == 42
        assert new_config.ssid_mode == SsidMode.SPECIAL
        # Preserved
        assert new_config.concurrent_mode is True


class TestWebRoutesConfigLoading:
    """Tests for web routes config loading."""

    def test_routes_load_initial_config(self, temp_dir):
        """Web routes should load config from file at import time."""
        # This is tested indirectly through the web routes tests
        # Here we verify the helper function exists and works
        from hotspotchi.web.routes import _load_initial_config

        # With no config file, should return defaults
        with patch(
            "hotspotchi.web.routes.DEFAULT_CONFIG_PATH",
            temp_dir / "nonexistent.yaml",
        ):
            # Re-call the function (it was already called at import)
            config = _load_initial_config()
            assert config.concurrent_mode is False

    def test_routes_config_preserves_concurrent_mode(self, temp_dir):
        """Web routes should preserve concurrent_mode from config file."""
        config_path = temp_dir / "config.yaml"
        with open(config_path, "w") as f:
            yaml.safe_dump({"concurrent_mode": True}, f)

        from hotspotchi.web.routes import _load_initial_config

        with patch("hotspotchi.web.routes.DEFAULT_CONFIG_PATH", config_path):
            config = _load_initial_config()
            assert config.concurrent_mode is True


class TestCLIConfigLoading:
    """Tests for CLI config loading helpers."""

    def test_load_base_config_with_file(self, temp_dir):
        """CLI should load config from file when available."""
        config_path = temp_dir / "config.yaml"
        with open(config_path, "w") as f:
            yaml.safe_dump({"concurrent_mode": True, "mac_mode": "cycle"}, f)

        from hotspotchi.cli import _load_base_config

        with patch("hotspotchi.cli.DEFAULT_CONFIG_PATH", config_path):
            config = _load_base_config()
            assert config.concurrent_mode is True
            assert config.mac_mode == MacMode.CYCLE

    def test_load_base_config_without_file(self, temp_dir):
        """CLI should use defaults when config file doesn't exist."""
        from hotspotchi.cli import _load_base_config

        with patch(
            "hotspotchi.cli.DEFAULT_CONFIG_PATH",
            temp_dir / "nonexistent.yaml",
        ):
            config = _load_base_config()
            assert config.concurrent_mode is False
            assert config.mac_mode == MacMode.DAILY_RANDOM

    def test_config_with_overrides_preserves_base(self, temp_dir):
        """_config_with_overrides should preserve base config values."""
        config_path = temp_dir / "config.yaml"
        with open(config_path, "w") as f:
            yaml.safe_dump({"concurrent_mode": True, "wifi_interface": "wlan1"}, f)

        from hotspotchi.cli import _config_with_overrides

        with patch("hotspotchi.cli.DEFAULT_CONFIG_PATH", config_path):
            config = _config_with_overrides(mac_mode=MacMode.FIXED)

            # Override applied
            assert config.mac_mode == MacMode.FIXED
            # Base values preserved
            assert config.concurrent_mode is True
            assert config.wifi_interface == "wlan1"


class TestWebAppConfigLoading:
    """Tests for web app server config loading."""

    def test_load_server_config_from_file(self, temp_dir):
        """Web app should load host/port from config file."""
        config_path = temp_dir / "config.yaml"
        with open(config_path, "w") as f:
            yaml.safe_dump({"web_host": "127.0.0.1", "web_port": 9000}, f)

        # Import the actual module using sys.modules
        import sys

        app_module = sys.modules["hotspotchi.web.app"]

        # Patch DEFAULT_CONFIG_PATH to point to our test config
        original_path = app_module.DEFAULT_CONFIG_PATH
        try:
            app_module.DEFAULT_CONFIG_PATH = config_path
            config = app_module._load_server_config()
            assert config.web_host == "127.0.0.1"
            assert config.web_port == 9000
        finally:
            app_module.DEFAULT_CONFIG_PATH = original_path

    def test_load_server_config_defaults(self, temp_dir):
        """Web app should use defaults when no config file."""
        import sys

        app_module = sys.modules["hotspotchi.web.app"]

        original_path = app_module.DEFAULT_CONFIG_PATH
        try:
            app_module.DEFAULT_CONFIG_PATH = temp_dir / "nonexistent.yaml"
            config = app_module._load_server_config()
            assert config.web_host == "0.0.0.0"
            assert config.web_port == 8080
        finally:
            app_module.DEFAULT_CONFIG_PATH = original_path


class TestPasswordValidation:
    """Tests for WiFi password validation."""

    def test_valid_password_8_chars(self):
        """Password with 8 characters should be valid."""
        config = HotSpotchiConfig(wifi_password="12345678")
        assert config.wifi_password == "12345678"

    def test_valid_password_16_chars(self):
        """Password with 16 characters should be valid."""
        config = HotSpotchiConfig(wifi_password="1234567890123456")
        assert config.wifi_password == "1234567890123456"

    def test_valid_password_none(self):
        """None password (daily random) should be valid."""
        config = HotSpotchiConfig(wifi_password=None)
        assert config.wifi_password is None

    def test_valid_password_empty(self):
        """Empty password (open network) should be valid."""
        config = HotSpotchiConfig(wifi_password="")
        assert config.wifi_password == ""

    def test_invalid_password_too_short(self):
        """Password shorter than 8 characters should fail."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            HotSpotchiConfig(wifi_password="short")

    def test_invalid_password_7_chars(self):
        """Password with exactly 7 characters should fail."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            HotSpotchiConfig(wifi_password="1234567")


class TestSSIDValidation:
    """Tests for custom SSID validation."""

    def test_valid_ssid_short(self):
        """Short SSID should be valid."""
        config = HotSpotchiConfig(custom_ssid="MyNet")
        assert config.custom_ssid == "MyNet"

    def test_valid_ssid_32_chars(self):
        """SSID with exactly 32 characters should be valid."""
        ssid = "A" * 32
        config = HotSpotchiConfig(custom_ssid=ssid)
        assert config.custom_ssid == ssid

    def test_valid_ssid_none(self):
        """None SSID should be valid."""
        config = HotSpotchiConfig(custom_ssid=None)
        assert config.custom_ssid is None

    def test_invalid_ssid_too_long(self):
        """SSID longer than 32 characters should fail."""
        with pytest.raises(ValueError, match="cannot exceed 32 characters"):
            HotSpotchiConfig(custom_ssid="A" * 33)


class TestGetEffectiveSsid:
    """Tests for get_effective_ssid method."""

    def test_normal_mode_uses_default(self):
        """Normal mode should use default SSID."""
        config = HotSpotchiConfig(ssid_mode=SsidMode.NORMAL, default_ssid="HotSpotchi")
        assert config.get_effective_ssid() == "HotSpotchi"

    def test_normal_mode_custom_default(self):
        """Normal mode should use custom default if set."""
        config = HotSpotchiConfig(ssid_mode=SsidMode.NORMAL, default_ssid="MyDefaultSSID")
        assert config.get_effective_ssid() == "MyDefaultSSID"

    def test_custom_mode_uses_custom_ssid(self):
        """Custom mode should use custom SSID."""
        config = HotSpotchiConfig(ssid_mode=SsidMode.CUSTOM, custom_ssid="MyNetwork")
        assert config.get_effective_ssid() == "MyNetwork"

    def test_custom_mode_without_custom_ssid_uses_default(self):
        """Custom mode without custom SSID should fall back to default."""
        config = HotSpotchiConfig(ssid_mode=SsidMode.CUSTOM, custom_ssid=None)
        assert config.get_effective_ssid() == "HotSpotchi"

    def test_special_mode_uses_special_ssid(self):
        """Special mode should use SSID from SPECIAL_SSIDS."""
        if not SPECIAL_SSIDS:
            return  # Skip if no special SSIDs
        config = HotSpotchiConfig(ssid_mode=SsidMode.SPECIAL, special_ssid_index=0)
        assert config.get_effective_ssid() == SPECIAL_SSIDS[0].ssid

    def test_special_mode_respects_index(self):
        """Special mode should respect special_ssid_index."""
        if len(SPECIAL_SSIDS) < 3:
            return  # Skip if not enough special SSIDs
        config = HotSpotchiConfig(ssid_mode=SsidMode.SPECIAL, special_ssid_index=2)
        assert config.get_effective_ssid() == SPECIAL_SSIDS[2].ssid

    def test_special_mode_invalid_index_uses_default(self):
        """Special mode with invalid index should fall back to default."""
        config = HotSpotchiConfig(ssid_mode=SsidMode.SPECIAL, special_ssid_index=9999)
        assert config.get_effective_ssid() == "HotSpotchi"


class TestSaveConfig:
    """Tests for save_config function."""

    def test_saves_to_file(self, temp_dir):
        """save_config should write config to file."""
        config_path = temp_dir / "config.yaml"
        config = HotSpotchiConfig(
            wifi_interface="wlan1",
            concurrent_mode=True,
            mac_mode=MacMode.RANDOM,
        )

        save_config(config, config_path)

        assert config_path.exists()
        with open(config_path) as f:
            data = yaml.safe_load(f)
        assert data["wifi_interface"] == "wlan1"
        assert data["concurrent_mode"] is True

    def test_creates_parent_directories(self, temp_dir):
        """save_config should create parent directories if needed."""
        config_path = temp_dir / "subdir" / "nested" / "config.yaml"
        config = HotSpotchiConfig()

        save_config(config, config_path)

        assert config_path.exists()

    def test_roundtrip(self, temp_dir):
        """Config saved and loaded should be equivalent."""
        config_path = temp_dir / "config.yaml"
        original = HotSpotchiConfig(
            wifi_interface="wlan1",
            concurrent_mode=True,
            mac_mode=MacMode.CYCLE,
            web_port=9000,
            wifi_password="testpass123",
        )

        save_config(original, config_path)
        loaded = load_config(config_path)

        assert loaded.wifi_interface == original.wifi_interface
        assert loaded.concurrent_mode == original.concurrent_mode
        assert loaded.mac_mode == original.mac_mode
        assert loaded.web_port == original.web_port
        assert loaded.wifi_password == original.wifi_password


class TestConfigDefaults:
    """Tests for default config values."""

    def test_default_wifi_interface(self):
        """Default wifi_interface should be wlan0."""
        config = HotSpotchiConfig()
        assert config.wifi_interface == "wlan0"

    def test_default_concurrent_mode(self):
        """Default concurrent_mode should be False."""
        config = HotSpotchiConfig()
        assert config.concurrent_mode is False

    def test_default_ap_interface(self):
        """Default ap_interface should be uap0."""
        config = HotSpotchiConfig()
        assert config.ap_interface == "uap0"

    def test_default_ssid_mode(self):
        """Default ssid_mode should be NORMAL."""
        config = HotSpotchiConfig()
        assert config.ssid_mode == SsidMode.NORMAL

    def test_default_mac_mode(self):
        """Default mac_mode should be DAILY_RANDOM."""
        config = HotSpotchiConfig()
        assert config.mac_mode == MacMode.DAILY_RANDOM

    def test_default_include_special_ssids(self):
        """Default include_special_ssids should be True."""
        config = HotSpotchiConfig()
        assert config.include_special_ssids is True

    def test_default_wifi_password(self):
        """Default wifi_password should be None (daily random)."""
        config = HotSpotchiConfig()
        assert config.wifi_password is None

    def test_default_ap_ip(self):
        """Default ap_ip should be 192.168.4.1."""
        config = HotSpotchiConfig()
        assert config.ap_ip == "192.168.4.1"

    def test_default_web_host(self):
        """Default web_host should be 0.0.0.0."""
        config = HotSpotchiConfig()
        assert config.web_host == "0.0.0.0"

    def test_default_web_port(self):
        """Default web_port should be 8080."""
        config = HotSpotchiConfig()
        assert config.web_port == 8080


class TestConfigExtraIgnore:
    """Tests for config extra fields handling."""

    def test_ignores_unknown_fields(self):
        """Config should ignore unknown fields."""
        config = HotSpotchiConfig(unknown_field="value", another_unknown=123)
        # Should not raise, and unknown fields should be ignored
        assert not hasattr(config, "unknown_field")
