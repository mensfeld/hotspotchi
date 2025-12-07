"""Tests for config loading across the application."""

from pathlib import Path
from unittest.mock import patch

import yaml

from hotspotchi.config import HotSpotchiConfig, MacMode, SsidMode, load_config


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
        new_config = HotSpotchiConfig(
            **{**original.model_dump(), "mac_mode": MacMode.FIXED}
        )

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
            yaml.safe_dump(
                {"concurrent_mode": True, "wifi_interface": "wlan1"}, f
            )

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
