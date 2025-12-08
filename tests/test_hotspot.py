"""Tests for hotspot module."""

from unittest.mock import MagicMock, patch

import pytest

from hotspotchi.config import HotspotchiConfig
from hotspotchi.hotspot import HotspotManager


@pytest.fixture
def config():
    """Create a test config."""
    return HotspotchiConfig(
        wifi_interface="wlan0",
        concurrent_mode=False,
    )


@pytest.fixture
def concurrent_config():
    """Create a test config with concurrent mode."""
    return HotspotchiConfig(
        wifi_interface="wlan0",
        concurrent_mode=True,
        ap_interface="uap0",
    )


class TestHotspotManagerInit:
    """Tests for HotspotManager initialization."""

    def test_init_with_config(self, config: HotspotchiConfig):
        """Manager should initialize with config."""
        manager = HotspotManager(config)
        assert manager.config == config

    def test_init_concurrent_mode(self, concurrent_config: HotspotchiConfig):
        """Manager should handle concurrent mode config."""
        manager = HotspotManager(concurrent_config)
        assert manager.config.concurrent_mode is True
        assert manager.config.ap_interface == "uap0"


class TestHotspotManagerChecks:
    """Tests for HotspotManager system checks."""

    def test_check_root_as_root(self, config: HotspotchiConfig):
        """check_root should return True when running as root."""
        manager = HotspotManager(config)
        with patch("os.geteuid", return_value=0):
            assert manager.check_root() is True

    def test_check_root_not_root(self, config: HotspotchiConfig):
        """check_root should return False when not root."""
        manager = HotspotManager(config)
        with patch("os.geteuid", return_value=1000):
            assert manager.check_root() is False

    @patch("shutil.which")
    def test_check_dependencies_all_present(self, mock_which: MagicMock, config: HotspotchiConfig):
        """check_dependencies should return empty list when all present."""
        mock_which.return_value = "/usr/sbin/hostapd"
        manager = HotspotManager(config)
        missing = manager.check_dependencies()
        assert missing == []

    @patch("shutil.which")
    def test_check_dependencies_missing_hostapd(
        self, mock_which: MagicMock, config: HotspotchiConfig
    ):
        """check_dependencies should list missing hostapd."""
        mock_which.side_effect = lambda x: None if x == "hostapd" else f"/usr/bin/{x}"
        manager = HotspotManager(config)
        missing = manager.check_dependencies()
        assert "hostapd" in missing

    @patch("shutil.which")
    def test_check_dependencies_missing_dnsmasq(
        self, mock_which: MagicMock, config: HotspotchiConfig
    ):
        """check_dependencies should list missing dnsmasq."""
        mock_which.side_effect = lambda x: None if x == "dnsmasq" else f"/usr/bin/{x}"
        manager = HotspotManager(config)
        missing = manager.check_dependencies()
        assert "dnsmasq" in missing

    @patch("shutil.which")
    def test_check_dependencies_concurrent_mode_needs_iw(
        self, mock_which: MagicMock, concurrent_config: HotspotchiConfig
    ):
        """check_dependencies in concurrent mode should check for iw."""
        mock_which.side_effect = lambda x: None if x == "iw" else f"/usr/bin/{x}"
        manager = HotspotManager(concurrent_config)
        missing = manager.check_dependencies()
        assert "iw" in missing


class TestHotspotManagerIsRunning:
    """Tests for is_running check."""

    @patch("subprocess.run")
    def test_is_running_true(self, mock_run: MagicMock, config: HotspotchiConfig):
        """is_running should return True when hostapd is running."""
        mock_run.return_value = MagicMock(returncode=0)
        manager = HotspotManager(config)
        assert manager.is_running() is True

    @patch("subprocess.run")
    def test_is_running_false(self, mock_run: MagicMock, config: HotspotchiConfig):
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

    def test_get_effective_interface_normal(self, config: HotspotchiConfig):
        """Should return wifi_interface in normal mode."""
        manager = HotspotManager(config)
        assert manager._get_effective_interface() == "wlan0"

    def test_get_effective_interface_concurrent(self, concurrent_config: HotspotchiConfig):
        """Should return ap_interface in concurrent mode."""
        manager = HotspotManager(concurrent_config)
        assert manager._get_effective_interface() == "uap0"

    def test_is_5ghz_channel_true(self, config: HotspotchiConfig):
        """Should return True for 5GHz channels."""
        manager = HotspotManager(config)
        assert manager._is_5ghz_channel(36) is True
        assert manager._is_5ghz_channel(40) is True
        assert manager._is_5ghz_channel(149) is True

    def test_is_5ghz_channel_false(self, config: HotspotchiConfig):
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
        self, mock_path: MagicMock, concurrent_config: HotspotchiConfig
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
        concurrent_config: HotspotchiConfig,
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
        self, mock_path: MagicMock, mock_run: MagicMock, concurrent_config: HotspotchiConfig
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
        self, mock_path: MagicMock, mock_run: MagicMock, concurrent_config: HotspotchiConfig
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
    def test_get_current_channel_success(self, mock_run: MagicMock, config: HotspotchiConfig):
        """Should parse channel from iw output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Interface wlan0\nchannel 6 (2437 MHz)\n",
        )
        manager = HotspotManager(config)
        channel = manager._get_current_channel()
        assert channel == 6

    @patch("subprocess.run")
    def test_get_current_channel_default(self, mock_run: MagicMock, config: HotspotchiConfig):
        """Should return default channel on failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        manager = HotspotManager(config)
        channel = manager._get_current_channel()
        assert channel == 7  # Default

    @patch("subprocess.run")
    def test_get_current_channel_no_channel_info(
        self, mock_run: MagicMock, config: HotspotchiConfig
    ):
        """Should return default if no channel in output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Interface wlan0\ntype managed\n",
        )
        manager = HotspotManager(config)
        channel = manager._get_current_channel()
        assert channel == 7  # Default


class TestHotspotManagerMACAddress:
    """Tests for MAC address operations."""

    @patch("hotspotchi.hotspot.Path")
    def test_get_current_mac_success(self, mock_path: MagicMock, config: HotspotchiConfig):
        """Should read MAC from sysfs."""
        mock_path.return_value.read_text.return_value = "aa:bb:cc:dd:ee:ff\n"
        manager = HotspotManager(config)
        mac = manager._get_current_mac("wlan0")
        assert mac == "aa:bb:cc:dd:ee:ff"

    @patch("hotspotchi.hotspot.Path")
    def test_get_current_mac_not_found(self, mock_path: MagicMock, config: HotspotchiConfig):
        """Should return None if file not found."""
        mock_path.return_value.read_text.side_effect = FileNotFoundError()
        manager = HotspotManager(config)
        mac = manager._get_current_mac("wlan0")
        assert mac is None

    @patch("hotspotchi.hotspot.Path")
    def test_get_current_mac_permission_denied(
        self, mock_path: MagicMock, config: HotspotchiConfig
    ):
        """Should return None if permission denied."""
        mock_path.return_value.read_text.side_effect = PermissionError()
        manager = HotspotManager(config)
        mac = manager._get_current_mac("wlan0")
        assert mac is None

    @patch("hotspotchi.hotspot.time.sleep")
    @patch("subprocess.run")
    def test_set_mac_address_success(
        self, mock_run: MagicMock, _mock_sleep: MagicMock, config: HotspotchiConfig
    ):
        """Should set MAC address successfully."""
        mock_run.return_value = MagicMock(returncode=0)
        manager = HotspotManager(config)
        result = manager._set_mac_address("aa:bb:cc:dd:ee:ff")
        assert result is True

    @patch("hotspotchi.hotspot.time.sleep")
    @patch("subprocess.run")
    def test_set_mac_address_failure(
        self, mock_run: MagicMock, _mock_sleep: MagicMock, config: HotspotchiConfig
    ):
        """Should return False on failure."""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # ip link down
            MagicMock(returncode=1),  # ip link set address fails
        ]
        manager = HotspotManager(config)
        result = manager._set_mac_address("aa:bb:cc:dd:ee:ff")
        assert result is False


class TestHotspotManagerPassword:
    """Tests for password handling."""

    def test_get_effective_password_daily(self, config: HotspotchiConfig):
        """Should generate daily password when None."""
        # Default config has wifi_password=None
        manager = HotspotManager(config)
        password = manager._get_effective_password()
        assert password is not None
        assert len(password) == 16

    def test_get_effective_password_fixed(self):
        """Should return fixed password when set."""
        config = HotspotchiConfig(wifi_password="mypassword123")
        manager = HotspotManager(config)
        password = manager._get_effective_password()
        assert password == "mypassword123"

    def test_get_effective_password_open(self):
        """Should return None for open network."""
        config = HotspotchiConfig(wifi_password="")
        manager = HotspotManager(config)
        password = manager._get_effective_password()
        assert password is None


class TestHotspotManagerConfigGeneration:
    """Tests for config file generation."""

    @patch("subprocess.run")
    def test_create_hostapd_config_with_password(
        self, mock_run: MagicMock, config: HotspotchiConfig
    ):
        """Should create hostapd config with WPA2."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")  # No channel info
        manager = HotspotManager(config)
        config_path = manager._create_hostapd_config("TestSSID")

        content = config_path.read_text()
        assert "interface=wlan0" in content
        assert "ssid=TestSSID" in content
        assert "wpa=2" in content
        assert "wpa_passphrase=" in content

        # Clean up
        config_path.unlink()

    @patch("subprocess.run")
    def test_create_hostapd_config_open_network(self, mock_run: MagicMock):
        """Should create hostapd config without WPA for open network."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        config = HotspotchiConfig(wifi_password="")
        manager = HotspotManager(config)
        config_path = manager._create_hostapd_config("OpenSSID")

        content = config_path.read_text()
        assert "ssid=OpenSSID" in content
        assert "wpa=" not in content

        config_path.unlink()

    @patch("subprocess.run")
    def test_create_hostapd_config_5ghz(self, mock_run: MagicMock):
        """Should use hw_mode=a for 5GHz channels."""
        mock_run.return_value = MagicMock(returncode=0, stdout="channel 36 (5180 MHz)")
        config = HotspotchiConfig(concurrent_mode=True)
        manager = HotspotManager(config)
        config_path = manager._create_hostapd_config("5GHz_SSID")

        content = config_path.read_text()
        assert "hw_mode=a" in content
        assert "channel=36" in content

        config_path.unlink()

    def test_create_dnsmasq_config(self, config: HotspotchiConfig):
        """Should create dnsmasq config."""
        manager = HotspotManager(config)
        config_path = manager._create_dnsmasq_config()

        content = config_path.read_text()
        assert "interface=wlan0" in content
        assert f"dhcp-range={config.dhcp_range_start}" in content

        config_path.unlink()


class TestHotspotManagerServiceControl:
    """Tests for service control methods."""

    @patch("subprocess.run")
    def test_stop_conflicting_services(self, mock_run: MagicMock, config: HotspotchiConfig):
        """Should stop conflicting services."""
        mock_run.return_value = MagicMock(returncode=0)
        manager = HotspotManager(config)
        manager._stop_conflicting_services()
        # Should have called systemctl stop and killall
        assert mock_run.call_count >= 4

    @patch("subprocess.run")
    def test_unblock_wifi(self, mock_run: MagicMock, config: HotspotchiConfig):
        """Should unblock WiFi."""
        mock_run.return_value = MagicMock(returncode=0)
        manager = HotspotManager(config)
        manager._unblock_wifi()
        # Should have called rfkill unblock
        call_args = str(mock_run.call_args)
        assert "rfkill" in call_args

    @patch("subprocess.run")
    def test_configure_interface(self, mock_run: MagicMock, config: HotspotchiConfig):
        """Should configure IP address."""
        mock_run.return_value = MagicMock(returncode=0)
        manager = HotspotManager(config)
        manager._configure_interface()
        # Should have called ip addr flush, ip addr add, ip link set up
        assert mock_run.call_count >= 3


class TestHotspotManagerStartStop:
    """Tests for start/stop with mocked dependencies."""

    @patch("os.geteuid")
    def test_start_requires_root(self, mock_geteuid: MagicMock, config: HotspotchiConfig):
        """Should raise error if not root."""
        mock_geteuid.return_value = 1000  # Not root
        manager = HotspotManager(config)
        with pytest.raises(RuntimeError, match="Must run as root"):
            manager.start()

    @patch("shutil.which")
    @patch("os.geteuid")
    def test_start_checks_dependencies(
        self, mock_geteuid: MagicMock, mock_which: MagicMock, config: HotspotchiConfig
    ):
        """Should raise error if dependencies missing."""
        mock_geteuid.return_value = 0  # Root
        mock_which.return_value = None  # All deps missing
        manager = HotspotManager(config)
        with pytest.raises(RuntimeError, match="Missing dependencies"):
            manager.start()

    @patch("subprocess.run")
    def test_stop_cleans_up(self, mock_run: MagicMock, config: HotspotchiConfig):
        """Should clean up processes and files."""
        mock_run.return_value = MagicMock(returncode=0)
        manager = HotspotManager(config)
        manager._hostapd_process = MagicMock()
        manager._hostapd_process.terminate = MagicMock()
        manager._hostapd_process.wait = MagicMock()
        manager._dnsmasq_process = MagicMock()
        manager._dnsmasq_process.terminate = MagicMock()
        manager._dnsmasq_process.wait = MagicMock()

        # Capture references before stop() sets them to None
        hostapd_mock = manager._hostapd_process
        dnsmasq_mock = manager._dnsmasq_process

        manager.stop()

        hostapd_mock.terminate.assert_called_once()
        dnsmasq_mock.terminate.assert_called_once()

    @patch("subprocess.run")
    def test_stop_restores_mac(self, mock_run: MagicMock, config: HotspotchiConfig):
        """Should restore original MAC address."""
        mock_run.return_value = MagicMock(returncode=0)
        manager = HotspotManager(config)
        manager._original_mac = "aa:bb:cc:dd:ee:ff"

        manager.stop()

        # Should have called ip link to restore MAC
        calls_str = str(mock_run.call_args_list)
        assert "aa:bb:cc:dd:ee:ff" in calls_str

    @patch("subprocess.run")
    @patch("hotspotchi.hotspot.Path")
    def test_stop_concurrent_removes_interface(self, mock_path: MagicMock, mock_run: MagicMock):
        """Should remove virtual interface in concurrent mode."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_path.return_value.exists.return_value = True

        config = HotspotchiConfig(concurrent_mode=True, ap_interface="uap0")
        manager = HotspotManager(config)
        manager._virtual_interface_created = True

        manager.stop()

        # Should have called iw dev del
        calls_str = str(mock_run.call_args_list)
        assert "uap0" in calls_str

    @patch("subprocess.run")
    def test_stop_handles_hostapd_timeout(self, mock_run: MagicMock, config: HotspotchiConfig):
        """Should kill process if terminate times out."""
        import subprocess

        mock_run.return_value = MagicMock(returncode=0)
        manager = HotspotManager(config)

        # Create mock process that times out on wait
        mock_process = MagicMock()
        mock_process.wait.side_effect = subprocess.TimeoutExpired("hostapd", 5)
        manager._hostapd_process = mock_process

        manager.stop()

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    @patch("subprocess.run")
    def test_stop_handles_dnsmasq_timeout(self, mock_run: MagicMock, config: HotspotchiConfig):
        """Should kill dnsmasq if terminate times out."""
        import subprocess

        mock_run.return_value = MagicMock(returncode=0)
        manager = HotspotManager(config)

        # Create mock process that times out on wait
        mock_process = MagicMock()
        mock_process.wait.side_effect = subprocess.TimeoutExpired("dnsmasq", 5)
        manager._dnsmasq_process = mock_process

        manager.stop()

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    @patch("subprocess.run")
    def test_stop_cleans_config_files(self, mock_run: MagicMock, config: HotspotchiConfig):
        """Should remove config files if they exist."""
        import tempfile
        from pathlib import Path

        mock_run.return_value = MagicMock(returncode=0)
        manager = HotspotManager(config)

        # Create temp files to represent configs
        with tempfile.NamedTemporaryFile(delete=False, suffix=".conf") as f:
            hostapd_path = Path(f.name)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".conf") as f:
            dnsmasq_path = Path(f.name)

        manager._hostapd_config = hostapd_path
        manager._dnsmasq_config = dnsmasq_path

        manager.stop()

        assert not hostapd_path.exists()
        assert not dnsmasq_path.exists()


class TestHotspotManagerRestart:
    """Tests for restart method."""

    @patch("subprocess.run")
    def test_restart_stops_and_starts(self, mock_run: MagicMock, config: HotspotchiConfig):
        """Should stop and start when running."""
        mock_run.return_value = MagicMock(returncode=0)
        manager = HotspotManager(config)

        # Mock is_running to return True first, then False after stop
        with (
            patch.object(manager, "is_running", side_effect=[True, False]),
            patch.object(manager, "stop") as mock_stop,
            patch.object(manager, "start") as mock_start,
        ):
            mock_start.return_value = MagicMock()
            manager.restart()
            mock_stop.assert_called_once()
            mock_start.assert_called_once()

    @patch("subprocess.run")
    def test_restart_with_new_config(self, mock_run: MagicMock, config: HotspotchiConfig):
        """Should update config on restart."""
        mock_run.return_value = MagicMock(returncode=0)
        manager = HotspotManager(config)

        new_config = HotspotchiConfig(wifi_interface="wlan1")

        with (
            patch.object(manager, "is_running", return_value=False),
            patch.object(manager, "start") as mock_start,
        ):
            mock_start.return_value = MagicMock()
            manager.restart(new_config)
            assert manager.config == new_config
            mock_start.assert_called_once()

    @patch("subprocess.run")
    def test_restart_not_running_no_new_config(self, mock_run: MagicMock, config: HotspotchiConfig):
        """Should return current state if not running and no new config."""
        mock_run.return_value = MagicMock(returncode=0)
        manager = HotspotManager(config)

        with (
            patch.object(manager, "is_running", return_value=False),
            patch.object(manager, "get_state") as mock_state,
        ):
            mock_state.return_value = MagicMock()
            result = manager.restart()
            mock_state.assert_called_once()
            assert result == mock_state.return_value


class TestHotspotManagerUpdateConfig:
    """Tests for update_config method."""

    def test_update_config(self, config: HotspotchiConfig):
        """Should update config without restarting."""
        manager = HotspotManager(config)
        new_config = HotspotchiConfig(wifi_interface="wlan1", default_ssid="NewSSID")

        manager.update_config(new_config)

        assert manager.config == new_config
        assert manager.config.wifi_interface == "wlan1"
        assert manager.config.default_ssid == "NewSSID"


class TestHotspotManagerGetState:
    """Tests for get_state method."""

    @patch("subprocess.run")
    def test_get_state_not_running(self, mock_run: MagicMock, config: HotspotchiConfig):
        """Should return empty state when not running."""
        mock_run.return_value = MagicMock(returncode=1)  # pgrep returns 1 = not found
        manager = HotspotManager(config)

        state = manager.get_state()

        assert state.running is False
        assert state.ssid == ""
        assert state.mac_address is None

    @patch("subprocess.run")
    @patch("hotspotchi.hotspot.select_combined")
    def test_get_state_running_with_mac_character(
        self, mock_select: MagicMock, mock_run: MagicMock, config: HotspotchiConfig
    ):
        """Should return state with character info when running."""
        from hotspotchi.characters import CHARACTERS
        from hotspotchi.selection import SelectionResult

        mock_run.return_value = MagicMock(returncode=0)  # pgrep returns 0 = running
        mock_select.return_value = SelectionResult(
            character=CHARACTERS[0],
            special_ssid=None,
        )

        manager = HotspotManager(config)
        state = manager.get_state()

        assert state.running is True
        # Default is include_character_in_ssid=True
        assert state.ssid == f"{CHARACTERS[0].name}_Hotspotchi"
        assert state.character_name == CHARACTERS[0].name
        assert state.mac_address is not None

    @patch("subprocess.run")
    @patch("hotspotchi.hotspot.select_combined")
    def test_get_state_running_with_special_ssid(
        self, mock_select: MagicMock, mock_run: MagicMock, config: HotspotchiConfig
    ):
        """Should return state with special SSID info when running."""
        from hotspotchi.characters import SPECIAL_SSIDS
        from hotspotchi.selection import SelectionResult

        mock_run.return_value = MagicMock(returncode=0)
        mock_select.return_value = SelectionResult(
            character=None,
            special_ssid=SPECIAL_SSIDS[0],
        )

        manager = HotspotManager(config)
        state = manager.get_state()

        assert state.running is True
        assert state.ssid == SPECIAL_SSIDS[0].ssid
        assert state.character_name == SPECIAL_SSIDS[0].character_name
        assert state.mac_address is None

    @patch("subprocess.run")
    @patch("hotspotchi.hotspot.select_combined")
    def test_get_state_running_disabled_mode(
        self, mock_select: MagicMock, mock_run: MagicMock, config: HotspotchiConfig
    ):
        """Should return state with no character when disabled."""
        from hotspotchi.selection import SelectionResult

        mock_run.return_value = MagicMock(returncode=0)
        mock_select.return_value = SelectionResult(
            character=None,
            special_ssid=None,
        )

        manager = HotspotManager(config)
        state = manager.get_state()

        assert state.running is True
        assert state.ssid == config.default_ssid
        assert state.character_name is None
        assert state.mac_address is None


class TestHotspotManagerStartFull:
    """Tests for full start() method with mocked dependencies."""

    @patch("hotspotchi.hotspot.time.sleep")
    @patch("subprocess.Popen")
    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("os.geteuid")
    @patch("hotspotchi.hotspot.select_combined")
    @patch("hotspotchi.hotspot.Path")
    def test_start_normal_mode_with_mac_character(
        self,
        mock_path: MagicMock,
        mock_select: MagicMock,
        mock_geteuid: MagicMock,
        mock_which: MagicMock,
        mock_run: MagicMock,
        mock_popen: MagicMock,
        _mock_sleep: MagicMock,
        config: HotspotchiConfig,
    ):
        """Should start hotspot with MAC character in normal mode."""
        from hotspotchi.characters import CHARACTERS
        from hotspotchi.selection import SelectionResult

        # Setup mocks
        mock_geteuid.return_value = 0  # Root
        mock_which.return_value = "/usr/bin/hostapd"
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.read_text.return_value = "aa:bb:cc:dd:ee:ff\n"

        # Mock select_combined to return a character
        mock_select.return_value = SelectionResult(
            character=CHARACTERS[0],
            special_ssid=None,
        )

        # Mock Popen for hostapd/dnsmasq
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process running
        mock_popen.return_value = mock_process

        manager = HotspotManager(config)
        state = manager.start()

        assert state.running is True
        assert state.character_name == CHARACTERS[0].name

    @patch("hotspotchi.hotspot.time.sleep")
    @patch("subprocess.Popen")
    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("os.geteuid")
    @patch("hotspotchi.hotspot.select_combined")
    @patch("hotspotchi.hotspot.Path")
    def test_start_with_special_ssid(
        self,
        mock_path: MagicMock,
        mock_select: MagicMock,
        mock_geteuid: MagicMock,
        mock_which: MagicMock,
        mock_run: MagicMock,
        mock_popen: MagicMock,
        _mock_sleep: MagicMock,
        config: HotspotchiConfig,
    ):
        """Should start hotspot with special SSID."""
        from hotspotchi.characters import SPECIAL_SSIDS
        from hotspotchi.selection import SelectionResult

        mock_geteuid.return_value = 0
        mock_which.return_value = "/usr/bin/hostapd"
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        mock_path.return_value.exists.return_value = True

        mock_select.return_value = SelectionResult(
            character=None,
            special_ssid=SPECIAL_SSIDS[0],
        )

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        manager = HotspotManager(config)
        state = manager.start()

        assert state.running is True
        assert state.ssid == SPECIAL_SSIDS[0].ssid
        assert state.character_name == SPECIAL_SSIDS[0].character_name

    @patch("hotspotchi.hotspot.time.sleep")
    @patch("subprocess.Popen")
    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("os.geteuid")
    @patch("hotspotchi.hotspot.select_combined")
    @patch("hotspotchi.hotspot.Path")
    def test_start_disabled_mode(
        self,
        mock_path: MagicMock,
        mock_select: MagicMock,
        mock_geteuid: MagicMock,
        mock_which: MagicMock,
        mock_run: MagicMock,
        mock_popen: MagicMock,
        _mock_sleep: MagicMock,
        config: HotspotchiConfig,
    ):
        """Should start hotspot with no character in disabled mode."""
        from hotspotchi.selection import SelectionResult

        mock_geteuid.return_value = 0
        mock_which.return_value = "/usr/bin/hostapd"
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        mock_path.return_value.exists.return_value = True

        mock_select.return_value = SelectionResult(
            character=None,
            special_ssid=None,
        )

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        manager = HotspotManager(config)
        state = manager.start()

        assert state.running is True
        assert state.ssid == config.default_ssid
        assert state.character_name is None

    @patch("hotspotchi.hotspot.time.sleep")
    @patch("subprocess.Popen")
    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("os.geteuid")
    @patch("hotspotchi.hotspot.select_combined")
    @patch("hotspotchi.hotspot.Path")
    def test_start_hostapd_fails(
        self,
        mock_path: MagicMock,
        mock_select: MagicMock,
        mock_geteuid: MagicMock,
        mock_which: MagicMock,
        mock_run: MagicMock,
        mock_popen: MagicMock,
        _mock_sleep: MagicMock,
        config: HotspotchiConfig,
    ):
        """Should raise error when hostapd fails to start."""
        from hotspotchi.selection import SelectionResult

        mock_geteuid.return_value = 0
        mock_which.return_value = "/usr/bin/hostapd"
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        mock_path.return_value.exists.return_value = True

        mock_select.return_value = SelectionResult(
            character=None,
            special_ssid=None,
        )

        # hostapd process that fails immediately
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Process died
        mock_process.communicate.return_value = (b"Configuration error", b"")
        mock_popen.return_value = mock_process

        manager = HotspotManager(config)
        with pytest.raises(RuntimeError, match="hostapd failed to start"):
            manager.start()

    @patch("hotspotchi.hotspot.time.sleep")
    @patch("subprocess.Popen")
    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("os.geteuid")
    @patch("hotspotchi.hotspot.select_combined")
    @patch("hotspotchi.hotspot.Path")
    def test_start_concurrent_mode_interface_failure(
        self,
        mock_path: MagicMock,
        mock_select: MagicMock,
        mock_geteuid: MagicMock,
        mock_which: MagicMock,
        mock_run: MagicMock,
        _mock_popen: MagicMock,
        _mock_sleep: MagicMock,
        concurrent_config: HotspotchiConfig,
    ):
        """Should raise error when virtual interface creation fails."""
        from hotspotchi.selection import SelectionResult

        mock_geteuid.return_value = 0
        mock_which.return_value = "/usr/bin/hostapd"
        # Simulate interface creation failure
        mock_path.return_value.exists.return_value = False
        mock_run.return_value = MagicMock(returncode=1)

        mock_select.return_value = SelectionResult(
            character=None,
            special_ssid=None,
        )

        manager = HotspotManager(concurrent_config)
        with pytest.raises(RuntimeError, match="Failed to create virtual interface"):
            manager.start()


class TestIncludeCharacterInSSID:
    """Tests for include_character_in_ssid feature."""

    @patch("subprocess.run")
    @patch("hotspotchi.hotspot.select_combined")
    def test_get_state_ssid_includes_character_name_by_default(
        self, mock_select: MagicMock, mock_run: MagicMock
    ):
        """SSID should include character name when include_character_in_ssid=True (default)."""
        from hotspotchi.characters import CHARACTERS
        from hotspotchi.selection import SelectionResult

        config = HotspotchiConfig(include_character_in_ssid=True)
        mock_run.return_value = MagicMock(returncode=0)
        mock_select.return_value = SelectionResult(
            character=CHARACTERS[0],
            special_ssid=None,
        )

        manager = HotspotManager(config)
        state = manager.get_state()

        assert state.ssid == f"{CHARACTERS[0].name}_Hotspotchi"

    @patch("subprocess.run")
    @patch("hotspotchi.hotspot.select_combined")
    def test_get_state_ssid_uses_default_when_disabled(
        self, mock_select: MagicMock, mock_run: MagicMock
    ):
        """SSID should use default when include_character_in_ssid=False."""
        from hotspotchi.characters import CHARACTERS
        from hotspotchi.selection import SelectionResult

        config = HotspotchiConfig(include_character_in_ssid=False)
        mock_run.return_value = MagicMock(returncode=0)
        mock_select.return_value = SelectionResult(
            character=CHARACTERS[0],
            special_ssid=None,
        )

        manager = HotspotManager(config)
        state = manager.get_state()

        assert state.ssid == config.default_ssid

    @patch("subprocess.run")
    @patch("hotspotchi.hotspot.select_combined")
    def test_get_state_special_ssid_not_affected(self, mock_select: MagicMock, mock_run: MagicMock):
        """Special SSIDs should not be affected by include_character_in_ssid."""
        from hotspotchi.characters import SPECIAL_SSIDS
        from hotspotchi.selection import SelectionResult

        config = HotspotchiConfig(include_character_in_ssid=True)
        mock_run.return_value = MagicMock(returncode=0)
        mock_select.return_value = SelectionResult(
            character=None,
            special_ssid=SPECIAL_SSIDS[0],
        )

        manager = HotspotManager(config)
        state = manager.get_state()

        # Special SSIDs keep their required name
        assert state.ssid == SPECIAL_SSIDS[0].ssid

    @patch("hotspotchi.hotspot.time.sleep")
    @patch("subprocess.Popen")
    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("os.geteuid")
    @patch("hotspotchi.hotspot.select_combined")
    @patch("hotspotchi.hotspot.Path")
    def test_start_ssid_includes_character_name(
        self,
        mock_path: MagicMock,
        mock_select: MagicMock,
        mock_geteuid: MagicMock,
        mock_which: MagicMock,
        mock_run: MagicMock,
        mock_popen: MagicMock,
        _mock_sleep: MagicMock,
    ):
        """Start should use SSID with character name when enabled."""
        from hotspotchi.characters import CHARACTERS
        from hotspotchi.selection import SelectionResult

        config = HotspotchiConfig(include_character_in_ssid=True)

        mock_geteuid.return_value = 0
        mock_which.return_value = "/usr/bin/hostapd"
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.read_text.return_value = "aa:bb:cc:dd:ee:ff\n"

        mock_select.return_value = SelectionResult(
            character=CHARACTERS[0],
            special_ssid=None,
        )

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        manager = HotspotManager(config)
        state = manager.start()

        assert state.ssid == f"{CHARACTERS[0].name}_Hotspotchi"

    @patch("hotspotchi.hotspot.time.sleep")
    @patch("subprocess.Popen")
    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("os.geteuid")
    @patch("hotspotchi.hotspot.select_combined")
    @patch("hotspotchi.hotspot.Path")
    def test_start_ssid_uses_default_when_disabled(
        self,
        mock_path: MagicMock,
        mock_select: MagicMock,
        mock_geteuid: MagicMock,
        mock_which: MagicMock,
        mock_run: MagicMock,
        mock_popen: MagicMock,
        _mock_sleep: MagicMock,
    ):
        """Start should use default SSID when include_character_in_ssid=False."""
        from hotspotchi.characters import CHARACTERS
        from hotspotchi.selection import SelectionResult

        config = HotspotchiConfig(include_character_in_ssid=False)

        mock_geteuid.return_value = 0
        mock_which.return_value = "/usr/bin/hostapd"
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.read_text.return_value = "aa:bb:cc:dd:ee:ff\n"

        mock_select.return_value = SelectionResult(
            character=CHARACTERS[0],
            special_ssid=None,
        )

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        manager = HotspotManager(config)
        state = manager.start()

        assert state.ssid == config.default_ssid
