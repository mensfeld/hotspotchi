"""Tests for CLI commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from hotspotchi.cli import (
    check,
    interactive,
    list_characters,
    list_ssids,
    main,
    start,
    status,
)


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestMainCommand:
    """Tests for the main CLI group."""

    def test_help(self, runner: CliRunner):
        """Main --help should show available commands."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Hotspotchi" in result.output
        assert "start" in result.output
        assert "status" in result.output

    def test_version(self, runner: CliRunner):
        """Main --version should show version."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "Hotspotchi" in result.output


class TestListCharactersCommand:
    """Tests for list-characters command."""

    def test_list_all(self, runner: CliRunner):
        """list-characters should show all characters."""
        result = runner.invoke(list_characters)
        assert result.exit_code == 0
        assert "MAC-Based Characters" in result.output
        assert "Mametchi" in result.output

    def test_filter_by_season(self, runner: CliRunner):
        """list-characters --season should filter."""
        result = runner.invoke(list_characters, ["--season", "winter"])
        assert result.exit_code == 0
        # Should only show winter characters
        # Yukinkotchi is a winter character
        assert "Yukinkotchi" in result.output or "winter" in result.output.lower()

    def test_search_by_name(self, runner: CliRunner):
        """list-characters --search should filter by name."""
        result = runner.invoke(list_characters, ["--search", "mametchi"])
        assert result.exit_code == 0
        assert "Mametchi" in result.output

    def test_search_no_results(self, runner: CliRunner):
        """list-characters --search with no matches."""
        result = runner.invoke(list_characters, ["--search", "nonexistent"])
        assert result.exit_code == 0
        assert "0 total" in result.output


class TestListSsidsCommand:
    """Tests for list-ssids command."""

    def test_list_active(self, runner: CliRunner):
        """list-ssids should show active SSIDs."""
        result = runner.invoke(list_ssids)
        assert result.exit_code == 0
        assert "Special SSID Characters" in result.output

    def test_list_all(self, runner: CliRunner):
        """list-ssids --all should show all SSIDs."""
        result = runner.invoke(list_ssids, ["--all"])
        assert result.exit_code == 0
        assert "Special SSID Characters" in result.output


class TestStatusCommand:
    """Tests for status command."""

    def test_status_default(self, runner: CliRunner):
        """status should show current character selection."""
        result = runner.invoke(status)
        assert result.exit_code == 0
        assert "Hotspotchi Status" in result.output
        assert "MAC Mode:" in result.output
        assert "SSID Mode:" in result.output

    def test_status_with_mac_mode(self, runner: CliRunner):
        """status --mac-mode should override mode."""
        result = runner.invoke(status, ["--mac-mode", "fixed"])
        assert result.exit_code == 0
        assert "fixed" in result.output

    def test_status_with_character_index(self, runner: CliRunner):
        """status --character-index should use specific character."""
        result = runner.invoke(status, ["--character-index", "5"])
        assert result.exit_code == 0
        assert "Hotspotchi Status" in result.output

    def test_status_daily_random_shows_countdown(self, runner: CliRunner):
        """status in daily_random mode should show countdown."""
        result = runner.invoke(status, ["--mac-mode", "daily_random"])
        assert result.exit_code == 0
        assert "Next change:" in result.output

    def test_status_cycle_shows_upcoming(self, runner: CliRunner):
        """status in cycle mode should show upcoming characters."""
        result = runner.invoke(status, ["--mac-mode", "cycle"])
        assert result.exit_code == 0
        assert "Upcoming characters:" in result.output


class TestStartCommand:
    """Tests for start command."""

    @patch("hotspotchi.cli.run_hotspot")
    def test_start_default(self, mock_run: MagicMock, runner: CliRunner):
        """start should run hotspot with defaults."""
        result = runner.invoke(start)
        assert result.exit_code == 0
        assert mock_run.called

    @patch("hotspotchi.cli.run_hotspot")
    def test_start_with_mac_mode(self, mock_run: MagicMock, runner: CliRunner):
        """start --mac-mode should set mode."""
        result = runner.invoke(start, ["--mac-mode", "random"])
        assert result.exit_code == 0
        assert mock_run.called
        config = mock_run.call_args[0][0]
        assert config.mac_mode.value == "random"

    @patch("hotspotchi.cli.run_hotspot")
    def test_start_with_ssid_mode(self, mock_run: MagicMock, runner: CliRunner):
        """start --ssid-mode should set mode."""
        result = runner.invoke(start, ["--ssid-mode", "special"])
        assert result.exit_code == 0
        config = mock_run.call_args[0][0]
        assert config.ssid_mode.value == "special"

    @patch("hotspotchi.cli.run_hotspot")
    def test_start_with_custom_ssid(self, mock_run: MagicMock, runner: CliRunner):
        """start --ssid should set custom SSID."""
        result = runner.invoke(start, ["--ssid-mode", "custom", "--ssid", "TestSSID"])
        assert result.exit_code == 0
        config = mock_run.call_args[0][0]
        assert config.custom_ssid == "TestSSID"

    @patch("hotspotchi.cli.run_hotspot")
    def test_start_with_special_index(self, mock_run: MagicMock, runner: CliRunner):
        """start --special-index should set index."""
        result = runner.invoke(start, ["--ssid-mode", "special", "--special-index", "5"])
        assert result.exit_code == 0
        config = mock_run.call_args[0][0]
        assert config.special_ssid_index == 5

    @patch("hotspotchi.cli.run_hotspot")
    def test_start_with_character_index(self, mock_run: MagicMock, runner: CliRunner):
        """start --character-index should set index."""
        result = runner.invoke(start, ["--mac-mode", "fixed", "--character-index", "10"])
        assert result.exit_code == 0
        config = mock_run.call_args[0][0]
        assert config.fixed_character_index == 10

    @patch("hotspotchi.cli.run_hotspot")
    def test_start_with_interface(self, mock_run: MagicMock, runner: CliRunner):
        """start --interface should set interface."""
        result = runner.invoke(start, ["--interface", "wlan1"])
        assert result.exit_code == 0
        config = mock_run.call_args[0][0]
        assert config.wifi_interface == "wlan1"

    @patch("hotspotchi.cli.run_hotspot")
    def test_start_with_password(self, mock_run: MagicMock, runner: CliRunner):
        """start --password should set password."""
        result = runner.invoke(start, ["--password", "testpassword"])
        assert result.exit_code == 0
        config = mock_run.call_args[0][0]
        assert config.wifi_password == "testpassword"

    @patch("hotspotchi.cli.run_hotspot")
    def test_start_concurrent_mode(self, mock_run: MagicMock, runner: CliRunner):
        """start --concurrent should enable concurrent mode."""
        result = runner.invoke(start, ["--concurrent"])
        assert result.exit_code == 0
        assert "Concurrent mode: ENABLED" in result.output
        config = mock_run.call_args[0][0]
        assert config.concurrent_mode is True

    @patch("hotspotchi.cli.run_hotspot")
    def test_start_no_concurrent_mode(self, mock_run: MagicMock, runner: CliRunner):
        """start --no-concurrent should disable concurrent mode."""
        result = runner.invoke(start, ["--no-concurrent"])
        assert result.exit_code == 0
        assert "Concurrent mode: DISABLED" in result.output
        config = mock_run.call_args[0][0]
        assert config.concurrent_mode is False

    @patch("hotspotchi.cli.run_hotspot")
    def test_start_with_config_file(self, mock_run: MagicMock, runner: CliRunner, temp_dir: Path):
        """start --config should load config file."""
        config_file = temp_dir / "config.yaml"
        config_file.write_text("mac_mode: random\n")
        result = runner.invoke(start, ["--config", str(config_file)])
        assert result.exit_code == 0
        assert f"Loaded config from {config_file}" in result.output
        assert mock_run.called

    @patch("hotspotchi.cli.run_hotspot")
    def test_start_missing_config_file(
        self, mock_run: MagicMock, runner: CliRunner, temp_dir: Path
    ):
        """start --config with missing file should warn."""
        config_file = temp_dir / "missing.yaml"
        result = runner.invoke(start, ["--config", str(config_file)])
        assert result.exit_code == 0
        assert "not found" in result.output
        assert mock_run.called


class TestCheckCommand:
    """Tests for check command."""

    @patch("hotspotchi.cli.HotspotManager")
    def test_check_as_root(self, mock_manager_class: MagicMock, runner: CliRunner):
        """check should show root status."""
        mock_manager = MagicMock()
        mock_manager.check_root.return_value = True
        mock_manager.check_dependencies.return_value = []
        mock_manager_class.return_value = mock_manager

        with patch("hotspotchi.cli.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            result = runner.invoke(check)

        assert result.exit_code == 0
        assert "Hotspotchi System Check" in result.output
        assert "[OK] Running as root" in result.output

    @patch("hotspotchi.cli.HotspotManager")
    def test_check_not_root(self, mock_manager_class: MagicMock, runner: CliRunner):
        """check should warn if not root."""
        mock_manager = MagicMock()
        mock_manager.check_root.return_value = False
        mock_manager.check_dependencies.return_value = []
        mock_manager_class.return_value = mock_manager

        with patch("hotspotchi.cli.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            result = runner.invoke(check)

        assert result.exit_code == 0
        assert "Not running as root" in result.output

    @patch("hotspotchi.cli.HotspotManager")
    def test_check_missing_deps(self, mock_manager_class: MagicMock, runner: CliRunner):
        """check should list missing dependencies."""
        mock_manager = MagicMock()
        mock_manager.check_root.return_value = True
        mock_manager.check_dependencies.return_value = ["hostapd"]
        mock_manager_class.return_value = mock_manager

        with patch("hotspotchi.cli.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            result = runner.invoke(check)

        assert result.exit_code == 0
        assert "Missing: hostapd" in result.output


class TestInteractiveCommand:
    """Tests for interactive command."""

    def test_interactive_quit(self, runner: CliRunner):
        """interactive should quit on 'q'."""
        result = runner.invoke(interactive, input="q\n")
        assert result.exit_code == 0
        assert "Interactive Menu" in result.output

    @patch("hotspotchi.cli.run_hotspot")
    def test_interactive_random_mac(self, mock_run: MagicMock, runner: CliRunner):
        """interactive option 3 should start with random MAC."""
        result = runner.invoke(interactive, input="3\nq\n")
        assert result.exit_code == 0
        assert mock_run.called
        config = mock_run.call_args[0][0]
        assert config.mac_mode.value == "random"

    @patch("hotspotchi.cli.run_hotspot")
    def test_interactive_custom_ssid(self, mock_run: MagicMock, runner: CliRunner):
        """interactive option 6 should start with custom SSID."""
        result = runner.invoke(interactive, input="6\nMyCustomSSID\nq\n")
        assert result.exit_code == 0
        assert mock_run.called
        config = mock_run.call_args[0][0]
        assert config.ssid_mode.value == "custom"
        assert config.custom_ssid == "MyCustomSSID"

    def test_interactive_empty_custom_ssid(self, runner: CliRunner):
        """interactive should reject empty custom SSID."""
        # Use a space followed by newline to simulate empty input
        result = runner.invoke(interactive, input="6\n \nq\n")
        assert result.exit_code == 0
        assert "SSID cannot be empty" in result.output
