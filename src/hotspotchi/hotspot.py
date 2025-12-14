"""
WiFi hotspot management for Hotspotchi.

Handles the system-level integration with hostapd and dnsmasq
to create WiFi access points on Raspberry Pi.
"""

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from hotspotchi.config import HotspotchiConfig, MacMode
from hotspotchi.mac import create_mac_address, format_mac
from hotspotchi.selection import generate_daily_password, get_day_number, select_combined


@dataclass
class HotspotState:
    """Current state of the hotspot."""

    running: bool
    ssid: str
    mac_address: str | None
    character_name: str | None
    ip_address: str
    hostapd_pid: int | None = None
    dnsmasq_pid: int | None = None


class HotspotManager:
    """Manages WiFi access point lifecycle."""

    def __init__(self, config: HotspotchiConfig):
        self.config = config
        self._hostapd_process: subprocess.Popen | None = None
        self._dnsmasq_process: subprocess.Popen | None = None
        self._hostapd_config: Path | None = None
        self._dnsmasq_config: Path | None = None
        self._original_mac: str | None = None
        self._virtual_interface_created: bool = False

    def check_root(self) -> bool:
        """Check if running as root."""
        return os.geteuid() == 0

    def check_dependencies(self) -> list[str]:
        """Check for required system tools.

        Returns:
            List of missing dependencies (empty if all present)
        """
        required = ["hostapd", "dnsmasq", "ip", "rfkill"]
        # Concurrent mode requires iw for interface management
        if self.config.concurrent_mode:
            required.append("iw")
        missing = []
        for tool in required:
            if shutil.which(tool) is None:
                missing.append(tool)
        return missing

    @staticmethod
    def check_concurrent_support(wifi_interface: str = "wlan0") -> tuple[bool, str]:
        """Check if the WiFi chipset supports concurrent AP mode.

        This checks if the interface can run AP mode alongside station mode.

        Args:
            wifi_interface: WiFi interface to check

        Returns:
            Tuple of (supported, message)
        """
        if shutil.which("iw") is None:
            return False, "iw command not found. Install with: sudo apt install iw"

        # Check if interface exists
        if not Path(f"/sys/class/net/{wifi_interface}").exists():
            return False, f"Interface {wifi_interface} not found"

        # Check interface capabilities
        result = subprocess.run(
            "iw phy phy0 info 2>/dev/null | grep -A 10 'valid interface combinations'",
            shell=True,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0 or not result.stdout:
            return False, "Could not determine WiFi capabilities"

        # Look for AP + managed (station) combination
        output = result.stdout.lower()
        if "ap" in output and ("managed" in output or "station" in output):
            return True, "WiFi chipset supports concurrent AP + Station mode"

        return False, "WiFi chipset may not support concurrent mode"

    def _get_current_channel(self) -> int:
        """Get the current WiFi channel of the main interface.

        In concurrent mode, the AP must use the same channel as the station.

        Returns:
            Channel number, or 7 as default
        """
        result = self._run_command(f"iw {self.config.wifi_interface} info")
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "channel" in line.lower():
                    # Parse "channel 6 (2437 MHz)" format
                    parts = line.strip().split()
                    for i, part in enumerate(parts):
                        if part.lower() == "channel" and i + 1 < len(parts):
                            try:
                                return int(parts[i + 1])
                            except ValueError:
                                pass
        return 7  # Default channel

    def _is_5ghz_channel(self, channel: int) -> bool:
        """Check if a channel is in the 5GHz band.

        Args:
            channel: WiFi channel number

        Returns:
            True if 5GHz, False if 2.4GHz
        """
        # 2.4GHz channels are 1-14, 5GHz channels are 36+
        return channel >= 36

    def _create_virtual_interface(self) -> bool:
        """Create virtual AP interface for concurrent mode.

        Returns:
            True if successful or interface already exists
        """
        ap_iface = self.config.ap_interface
        wifi_iface = self.config.wifi_interface

        # Check if virtual interface already exists
        if Path(f"/sys/class/net/{ap_iface}").exists():
            return True

        # Create virtual interface
        result = self._run_command(f"iw dev {wifi_iface} interface add {ap_iface} type __ap")
        if result.returncode != 0:
            return False

        self._virtual_interface_created = True
        time.sleep(0.5)
        return True

    def _remove_virtual_interface(self) -> None:
        """Remove virtual AP interface if it exists."""
        ap_iface = self.config.ap_interface

        # Remove interface if it exists (regardless of who created it)
        if Path(f"/sys/class/net/{ap_iface}").exists():
            self._run_command(f"ip link set {ap_iface} down")
            self._run_command(f"iw dev {ap_iface} del")
            # Wait for kernel to fully clean up the interface
            time.sleep(5)

        self._virtual_interface_created = False

    def _get_effective_interface(self) -> str:
        """Get the interface to use for the AP.

        Returns:
            ap_interface in concurrent mode, wifi_interface otherwise
        """
        if self.config.concurrent_mode:
            return self.config.ap_interface
        return self.config.wifi_interface

    def _run_command(
        self,
        cmd: str,
        capture: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a shell command.

        Args:
            cmd: Command string to execute
            capture: If True, capture stdout/stderr

        Returns:
            CompletedProcess result
        """
        return subprocess.run(
            cmd,
            shell=True,
            capture_output=capture,
            text=True,
            check=False,
        )

    def _get_current_mac(self, interface: str | None = None) -> str | None:
        """Get current MAC address of the interface."""
        if interface is None:
            interface = self._get_effective_interface()
        path = Path(f"/sys/class/net/{interface}/address")
        try:
            return path.read_text().strip()
        except (FileNotFoundError, PermissionError):
            return None

    def _set_mac_address(self, mac: str) -> bool:
        """Set MAC address on interface.

        Args:
            mac: MAC address to set

        Returns:
            True if successful
        """
        interface = self._get_effective_interface()

        # Bring interface down
        self._run_command(f"ip link set {interface} down")
        time.sleep(0.5)

        # Set MAC address
        result = self._run_command(f"ip link set {interface} address {mac}")
        if result.returncode != 0:
            return False

        time.sleep(0.5)
        return True

    def _get_effective_password(self) -> str | None:
        """Get the password to use for the WiFi network.

        Returns:
            Password string, or None for open network
        """
        if self.config.wifi_password is None:
            # Generate daily random password
            return generate_daily_password()
        if self.config.wifi_password == "":
            # Empty string = open network
            return None
        # Use configured password
        return self.config.wifi_password

    def _create_hostapd_config(self, ssid: str, bssid: str | None = None) -> Path:
        """Create hostapd configuration file.

        Args:
            ssid: Network name to broadcast
            bssid: MAC address (BSSID) to use, or None for default

        Returns:
            Path to temporary config file
        """
        interface = self._get_effective_interface()

        # In concurrent mode, must use same channel as station
        channel = self._get_current_channel() if self.config.concurrent_mode else 7

        # Use hw_mode=a for 5GHz channels, hw_mode=g for 2.4GHz
        hw_mode = "a" if self._is_5ghz_channel(channel) else "g"

        config = f"""interface={interface}
driver=nl80211
ssid={ssid}
hw_mode={hw_mode}
channel={channel}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
"""
        # Set explicit BSSID for MAC-based character detection
        if bssid:
            config += f"bssid={bssid}\n"

        password = self._get_effective_password()
        if password:
            config += f"""wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""

        fd, path = tempfile.mkstemp(suffix=".conf", prefix="hotspotchi_hostapd_")
        with os.fdopen(fd, "w") as config_file:
            config_file.write(config)
        return Path(path)

    def _create_dnsmasq_config(self) -> Path:
        """Create dnsmasq configuration file.

        Returns:
            Path to temporary config file
        """
        interface = self._get_effective_interface()
        config = f"""interface={interface}
dhcp-range={self.config.dhcp_range_start},{self.config.dhcp_range_end},{self.config.ap_netmask},24h
"""

        fd, path = tempfile.mkstemp(suffix=".conf", prefix="hotspotchi_dnsmasq_")
        with os.fdopen(fd, "w") as config_file:
            config_file.write(config)
        return Path(path)

    def _stop_conflicting_services(self) -> None:
        """Stop any services that might conflict."""
        self._run_command("systemctl stop hostapd 2>/dev/null")
        self._run_command("systemctl stop dnsmasq 2>/dev/null")
        self._run_command("killall hostapd 2>/dev/null")
        self._run_command("killall dnsmasq 2>/dev/null")

    def _unblock_wifi(self) -> None:
        """Unblock WiFi if blocked by rfkill."""
        self._run_command("rfkill unblock wifi")

    def _configure_interface(self) -> None:
        """Configure IP address on interface."""
        interface = self._get_effective_interface()
        self._run_command(f"ip addr flush dev {interface}")
        self._run_command(f"ip addr add {self.config.ap_ip}/24 dev {interface}")
        self._run_command(f"ip link set {interface} up")

    def start(self) -> HotspotState:
        """Start the WiFi access point.

        Returns:
            Current hotspot state

        Raises:
            RuntimeError: If not running as root or dependencies missing
        """
        if not self.check_root():
            raise RuntimeError("Must run as root (use sudo)")

        missing = self.check_dependencies()
        if missing:
            raise RuntimeError(f"Missing dependencies: {', '.join(missing)}")

        # Stop conflicting services
        self._stop_conflicting_services()
        self._unblock_wifi()

        # Handle concurrent mode vs normal mode
        if self.config.concurrent_mode:
            # Create virtual AP interface
            if not self._create_virtual_interface():
                raise RuntimeError(
                    f"Failed to create virtual interface {self.config.ap_interface}. "
                    "Your WiFi chipset may not support concurrent AP mode."
                )
            # Don't touch NetworkManager - keep station connection active
        else:
            # Normal mode: disable NetworkManager control of the interface
            self._run_command(
                f"nmcli device set {self.config.wifi_interface} managed no 2>/dev/null"
            )

        # Get effective interface for AP
        ap_interface = self._get_effective_interface()

        # Select character using combined pool (MAC + special SSIDs)
        selection = select_combined(self.config)

        # Determine SSID and MAC based on selection
        mac_address = None
        char_name = None

        if selection.is_special_ssid:
            # Special SSID selected - use special SSID name, no MAC change needed
            ssid = selection.ssid or self.config.default_ssid
            char_name = selection.name
        elif selection.character:
            # MAC character selected - use default SSID, spoof MAC
            ssid = self.config.default_ssid
            char_name = selection.name
            self._original_mac = self._get_current_mac(ap_interface)
            mac_address = create_mac_address(selection.character)
            if not self._set_mac_address(mac_address):
                mac_address = None  # Failed to set, will use default
            else:
                mac_address = format_mac(mac_address)
        else:
            # No selection (disabled mode)
            ssid = self.config.default_ssid

        # Bring interface up
        self._run_command(f"ip link set {ap_interface} up")

        # Configure IP
        self._configure_interface()

        # Create config files (pass MAC for BSSID setting in hostapd)
        self._hostapd_config = self._create_hostapd_config(ssid, bssid=mac_address)
        self._dnsmasq_config = self._create_dnsmasq_config()

        # Start dnsmasq
        self._dnsmasq_process = subprocess.Popen(
            ["dnsmasq", "-C", str(self._dnsmasq_config), "-d"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1)

        # Start hostapd
        self._hostapd_process = subprocess.Popen(
            ["hostapd", str(self._hostapd_config)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(2)

        # Check if hostapd started successfully
        if self._hostapd_process.poll() is not None:
            stdout, stderr = self._hostapd_process.communicate()
            self.stop()
            # hostapd outputs errors to stdout, not stderr
            error_msg = stdout.decode() or stderr.decode()
            raise RuntimeError(f"hostapd failed to start: {error_msg}")

        return HotspotState(
            running=True,
            ssid=ssid,
            mac_address=mac_address,
            character_name=char_name,
            ip_address=self.config.ap_ip,
            hostapd_pid=self._hostapd_process.pid if self._hostapd_process else None,
            dnsmasq_pid=self._dnsmasq_process.pid if self._dnsmasq_process else None,
        )

    def stop(self) -> None:
        """Stop the WiFi access point and restore original state."""
        ap_interface = self._get_effective_interface()

        # Stop our own processes if we have them
        if self._hostapd_process:
            self._hostapd_process.terminate()
            try:
                self._hostapd_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._hostapd_process.kill()
            self._hostapd_process = None

        if self._dnsmasq_process:
            self._dnsmasq_process.terminate()
            try:
                self._dnsmasq_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._dnsmasq_process.kill()
            self._dnsmasq_process = None

        # Also kill any system-wide hostapd (for cross-process restart)
        # Only kill hostapd - dnsmasq might be used by NetworkManager for DNS
        self._run_command("pkill -x hostapd")
        # Kill only our dnsmasq instances (those with our config file)
        self._run_command("pkill -f 'dnsmasq.*hotspotchi'")

        # Restore original MAC (only if we changed it)
        if self._original_mac:
            self._run_command(f"ip link set {ap_interface} down")
            self._run_command(f"ip link set {ap_interface} address {self._original_mac}")
            self._run_command(f"ip link set {ap_interface} up")
            self._original_mac = None

        # Clean up config files
        for config_path in [self._hostapd_config, self._dnsmasq_config]:
            if config_path and config_path.exists():
                config_path.unlink()

        self._hostapd_config = None
        self._dnsmasq_config = None

        # Handle cleanup based on mode
        if self.config.concurrent_mode:
            # Remove virtual interface
            self._remove_virtual_interface()
        else:
            # Restart NetworkManager to restore normal WiFi
            self._run_command("systemctl restart NetworkManager 2>/dev/null")

    def is_running(self) -> bool:
        """Check if hotspot is currently running.

        Checks both our own process and any system-wide hostapd process.
        This allows the web dashboard to detect hotspots started by systemd.
        """
        # First check our own process
        if self._hostapd_process and self._hostapd_process.poll() is None:
            return True

        # Also check for any hostapd process running system-wide
        result = self._run_command("pgrep -x hostapd")
        return result.returncode == 0

    def restart(self, new_config: HotspotchiConfig | None = None) -> HotspotState:
        """Restart the hotspot with optional new configuration.

        Args:
            new_config: New configuration to use (optional)

        Returns:
            New hotspot state after restart
        """
        was_running = self.is_running()

        if was_running:
            self.stop()

        if new_config:
            self.config = new_config

        if was_running or new_config:
            return self.start()

        return self.get_state()

    def update_config(self, new_config: HotspotchiConfig) -> None:
        """Update configuration without restarting.

        Args:
            new_config: New configuration to store
        """
        self.config = new_config

    def get_state(self) -> HotspotState:
        """Get current hotspot state."""
        if not self.is_running():
            return HotspotState(
                running=False,
                ssid="",
                mac_address=None,
                character_name=None,
                ip_address="",
            )

        selection = select_combined(self.config)

        if selection.is_special_ssid:
            ssid = selection.ssid or self.config.default_ssid
            char_name = selection.name
            mac_address = None
        elif selection.character:
            ssid = self.config.default_ssid
            char_name = selection.name
            mac_address = format_mac(create_mac_address(selection.character))
        else:
            ssid = self.config.default_ssid
            char_name = None
            mac_address = None

        return HotspotState(
            running=True,
            ssid=ssid,
            mac_address=mac_address,
            character_name=char_name,
            ip_address=self.config.ap_ip,
            hostapd_pid=self._hostapd_process.pid if self._hostapd_process else None,
            dnsmasq_pid=self._dnsmasq_process.pid if self._dnsmasq_process else None,
        )


def run_hotspot(config: HotspotchiConfig) -> None:
    """Run the hotspot until interrupted.

    This is the main entry point for running Hotspotchi as a service.
    In daily_random mode, automatically restarts at midnight to pick up
    the new character for the day.

    Args:
        config: Configuration to use
    """
    manager = HotspotManager(config)

    def cleanup(_signum: int, _frame) -> None:
        print("\nShutting down...")
        manager.stop()
        print("Cleanup complete.")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        state = manager.start()
        current_day = get_day_number()

        print("Hotspotchi is running!")
        print(f"  SSID: {state.ssid}")
        print(f"  MAC: {state.mac_address or 'default'}")
        print(f"  Character: {state.character_name or 'none'}")
        print(f"  IP: {state.ip_address}")
        print("\nPress Ctrl+C to stop")

        while manager.is_running():
            time.sleep(10)  # Check every 10 seconds

            # In daily_random mode, restart at midnight to get new character
            if config.mac_mode == MacMode.DAILY_RANDOM:
                new_day = get_day_number()
                if new_day != current_day:
                    print("\nMidnight passed - restarting for new daily character...")
                    manager.stop()
                    state = manager.start()
                    current_day = new_day
                    print(f"  New character: {state.character_name or 'none'}")
                    print(f"  SSID: {state.ssid}")
                    print(f"  MAC: {state.mac_address or 'default'}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        manager.stop()
        sys.exit(1)
