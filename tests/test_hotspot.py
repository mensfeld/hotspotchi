"""Tests for hotspot module."""

from unittest.mock import MagicMock, patch

import pytest

from hotspotchi.config import HotSpotchiConfig
from hotspotchi.hotspot import HotspotManager


@pytest.fixture
def config():
    """Create a test config."""
    return HotSpotchiConfig(
        wifi_interface="wlan0",
        concurrent_mode=False,
    )


@pytest.fixture
def concurrent_config():
    """Create a test config with concurrent mode."""
    return HotSpotchiConfig(
        wifi_interface="wlan0",
        concurrent_mode=True,
        ap_interface="uap0",
    )


class TestHotspotManagerInit:
    """Tests for HotspotManager initialization."""

    def test_init_with_config(self, config: HotSpotchiConfig):
        """Manager should initialize with config."""
        manager = HotspotManager(config)
        assert manager.config == config

    def test_init_concurrent_mode(self, concurrent_config: HotSpotchiConfig):
        """Manager should handle concurrent mode config."""
        manager = HotspotManager(concurrent_config)
        assert manager.config.concurrent_mode is True
        assert manager.config.ap_interface == "uap0"


class TestHotspotManagerChecks:
    """Tests for HotspotManager system checks."""

    def test_check_root_as_root(self, config: HotSpotchiConfig):
        """check_root should return True when running as root."""
        manager = HotspotManager(config)
        with patch("os.geteuid", return_value=0):
            assert manager.check_root() is True

    def test_check_root_not_root(self, config: HotSpotchiConfig):
        """check_root should return False when not root."""
        manager = HotspotManager(config)
        with patch("os.geteuid", return_value=1000):
            assert manager.check_root() is False

    @patch("shutil.which")
    def test_check_dependencies_all_present(self, mock_which: MagicMock, config: HotSpotchiConfig):
        """check_dependencies should return empty list when all present."""
        mock_which.return_value = "/usr/sbin/hostapd"
        manager = HotspotManager(config)
        missing = manager.check_dependencies()
        assert missing == []

    @patch("shutil.which")
    def test_check_dependencies_missing_hostapd(
        self, mock_which: MagicMock, config: HotSpotchiConfig
    ):
        """check_dependencies should list missing hostapd."""
        mock_which.side_effect = lambda x: None if x == "hostapd" else f"/usr/bin/{x}"
        manager = HotspotManager(config)
        missing = manager.check_dependencies()
        assert "hostapd" in missing

    @patch("shutil.which")
    def test_check_dependencies_missing_dnsmasq(
        self, mock_which: MagicMock, config: HotSpotchiConfig
    ):
        """check_dependencies should list missing dnsmasq."""
        mock_which.side_effect = lambda x: None if x == "dnsmasq" else f"/usr/bin/{x}"
        manager = HotspotManager(config)
        missing = manager.check_dependencies()
        assert "dnsmasq" in missing

    @patch("shutil.which")
    def test_check_dependencies_concurrent_mode_needs_iw(
        self, mock_which: MagicMock, concurrent_config: HotSpotchiConfig
    ):
        """check_dependencies in concurrent mode should check for iw."""
        mock_which.side_effect = lambda x: None if x == "iw" else f"/usr/bin/{x}"
        manager = HotspotManager(concurrent_config)
        missing = manager.check_dependencies()
        assert "iw" in missing


class TestHotspotManagerIsRunning:
    """Tests for is_running check."""

    @patch("subprocess.run")
    def test_is_running_true(self, mock_run: MagicMock, config: HotSpotchiConfig):
        """is_running should return True when hostapd is running."""
        mock_run.return_value = MagicMock(returncode=0)
        manager = HotspotManager(config)
        assert manager.is_running() is True

    @patch("subprocess.run")
    def test_is_running_false(self, mock_run: MagicMock, config: HotSpotchiConfig):
        """is_running should return False when hostapd is not running."""
        mock_run.return_value = MagicMock(returncode=1)
        manager = HotspotManager(config)
        assert manager.is_running() is False


class TestConcurrentSupport:
    """Tests for concurrent mode support detection."""

    @patch("shutil.which")
    def test_concurrent_support_no_iw(self, mock_which: MagicMock):
        """Should fail gracefully when iw is not installed."""
        mock_which.return_value = None
        supported, msg = HotspotManager.check_concurrent_support()
        assert supported is False
        assert "iw command not found" in msg

    @patch("shutil.which")
    @patch("hotspotchi.hotspot.Path")
    def test_concurrent_support_no_interface(self, mock_path: MagicMock, mock_which: MagicMock):
        """Should fail when interface doesn't exist."""
        mock_which.return_value = "/usr/bin/iw"
        mock_path.return_value.exists.return_value = False
        supported, msg = HotspotManager.check_concurrent_support("wlan0")
        assert supported is False
        assert "not found" in msg

    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("hotspotchi.hotspot.Path")
    def test_concurrent_support_check_fails(
        self, mock_path: MagicMock, mock_which: MagicMock, mock_run: MagicMock
    ):
        """Should handle failed capability check."""
        mock_which.return_value = "/usr/bin/iw"
        mock_path.return_value.exists.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        supported, msg = HotspotManager.check_concurrent_support("wlan0")
        assert supported is False
        assert "Could not determine" in msg

    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("hotspotchi.hotspot.Path")
    def test_concurrent_support_supported(
        self, mock_path: MagicMock, mock_which: MagicMock, mock_run: MagicMock
    ):
        """Should detect when AP + station is supported."""
        mock_which.return_value = "/usr/bin/iw"
        mock_path.return_value.exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="AP, managed, 1 channel")
        supported, msg = HotspotManager.check_concurrent_support("wlan0")
        assert supported is True
        assert "supports" in msg.lower()


class TestHotspotManagerHelpers:
    """Tests for helper methods."""

    def test_get_effective_interface_normal(self, config: HotSpotchiConfig):
        """Should return wifi_interface in normal mode."""
        manager = HotspotManager(config)
        assert manager._get_effective_interface() == "wlan0"

    def test_get_effective_interface_concurrent(self, concurrent_config: HotSpotchiConfig):
        """Should return ap_interface in concurrent mode."""
        manager = HotspotManager(concurrent_config)
        assert manager._get_effective_interface() == "uap0"

    def test_is_5ghz_channel_true(self, config: HotSpotchiConfig):
        """Should return True for 5GHz channels."""
        manager = HotspotManager(config)
        assert manager._is_5ghz_channel(36) is True
        assert manager._is_5ghz_channel(40) is True
        assert manager._is_5ghz_channel(149) is True

    def test_is_5ghz_channel_false(self, config: HotSpotchiConfig):
        """Should return False for 2.4GHz channels."""
        manager = HotspotManager(config)
        assert manager._is_5ghz_channel(1) is False
        assert manager._is_5ghz_channel(6) is False
        assert manager._is_5ghz_channel(11) is False
        assert manager._is_5ghz_channel(14) is False


class TestHotspotManagerVirtualInterface:
    """Tests for virtual interface management."""

    @patch("hotspotchi.hotspot.Path")
    def test_create_virtual_interface_already_exists(
        self, mock_path: MagicMock, concurrent_config: HotSpotchiConfig
    ):
        """Should return True if interface already exists."""
        mock_path.return_value.exists.return_value = True
        manager = HotspotManager(concurrent_config)
        result = manager._create_virtual_interface()
        assert result is True

    @patch("hotspotchi.hotspot.time.sleep")
    @patch("subprocess.run")
    @patch("hotspotchi.hotspot.Path")
    def test_create_virtual_interface_success(
        self,
        mock_path: MagicMock,
        mock_run: MagicMock,
        _mock_sleep: MagicMock,
        concurrent_config: HotSpotchiConfig,
    ):
        """Should create interface if it doesn't exist."""
        mock_path.return_value.exists.return_value = False
        mock_run.return_value = MagicMock(returncode=0)
        manager = HotspotManager(concurrent_config)
        result = manager._create_virtual_interface()
        assert result is True
        assert manager._virtual_interface_created is True

    @patch("subprocess.run")
    @patch("hotspotchi.hotspot.Path")
    def test_create_virtual_interface_failure(
        self, mock_path: MagicMock, mock_run: MagicMock, concurrent_config: HotSpotchiConfig
    ):
        """Should return False on creation failure."""
        mock_path.return_value.exists.return_value = False
        mock_run.return_value = MagicMock(returncode=1)
        manager = HotspotManager(concurrent_config)
        result = manager._create_virtual_interface()
        assert result is False

    @patch("subprocess.run")
    @patch("hotspotchi.hotspot.Path")
    def test_remove_virtual_interface(
        self, mock_path: MagicMock, mock_run: MagicMock, concurrent_config: HotSpotchiConfig
    ):
        """Should remove interface if it exists."""
        mock_path.return_value.exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)
        manager = HotspotManager(concurrent_config)
        manager._virtual_interface_created = True
        manager._remove_virtual_interface()
        assert manager._virtual_interface_created is False


class TestHotspotManagerChannelDetection:
    """Tests for channel detection."""

    @patch("subprocess.run")
    def test_get_current_channel_success(self, mock_run: MagicMock, config: HotSpotchiConfig):
        """Should parse channel from iw output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Interface wlan0\nchannel 6 (2437 MHz)\n",
        )
        manager = HotspotManager(config)
        channel = manager._get_current_channel()
        assert channel == 6

    @patch("subprocess.run")
    def test_get_current_channel_default(self, mock_run: MagicMock, config: HotSpotchiConfig):
        """Should return default channel on failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        manager = HotspotManager(config)
        channel = manager._get_current_channel()
        assert channel == 7  # Default

    @patch("subprocess.run")
    def test_get_current_channel_no_channel_info(
        self, mock_run: MagicMock, config: HotSpotchiConfig
    ):
        """Should return default if no channel in output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Interface wlan0\ntype managed\n",
        )
        manager = HotspotManager(config)
        channel = manager._get_current_channel()
        assert channel == 7  # Default
