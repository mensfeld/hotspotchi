"""
WiFi hotspot management for HotSpotchi.

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
from typing import Optional

from hotspotchi.config import HotSpotchiConfig
from hotspotchi.mac import create_mac_address, format_mac
from hotspotchi.selection import generate_daily_password, select_character
from hotspotchi.ssid import resolve_ssid


@dataclass
class HotspotState:
    """Current state of the hotspot."""

    running: bool
    ssid: str
    mac_address: Optional[str]
    character_name: Optional[str]
    ip_address: str
    hostapd_pid: Optional[int] = None
    dnsmasq_pid: Optional[int] = None


class HotspotManager:
    """Manages WiFi access point lifecycle."""

    def __init__(self, config: HotSpotchiConfig):
        self.config = config
        self._hostapd_process: Optional[subprocess.Popen] = None
        self._dnsmasq_process: Optional[subprocess.Popen] = None
        self._hostapd_config: Optional[Path] = None
        self._dnsmasq_config: Optional[Path] = None
        self._original_mac: Optional[str] = None
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
        result = self._run_command(
            f"iw dev {wifi_iface} interface add {ap_iface} type __ap"
        )
        if result.returncode != 0:
            return False

        self._virtual_interface_created = True
        time.sleep(0.5)
        return True

    def _remove_virtual_interface(self) -> None:
        """Remove virtual AP interface."""
        if not self._virtual_interface_created:
            return

        ap_iface = self.config.ap_interface
        self._run_command(f"ip link set {ap_iface} down")
        self._run_command(f"iw dev {ap_iface} del")
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

    def _get_current_mac(self, interface: Optional[str] = None) -> Optional[str]:
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

    def _get_effective_password(self) -> Optional[str]:
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

    def _create_hostapd_config(self, ssid: str) -> Path:
        """Create hostapd configuration file.

        Args:
            ssid: Network name to broadcast

        Returns:
            Path to temporary config file
        """
        interface = self._get_effective_interface()

        # In concurrent mode, must use same channel as station
        channel = self._get_current_channel() if self.config.concurrent_mode else 7

        config = f"""interface={interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
"""

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

        # Get SSID and character info
        ssid, special_char = resolve_ssid(self.config)
        character = select_character(self.config)

        # Set MAC address if we have a character
        mac_address = None
        char_name = special_char  # Special char takes precedence

        if character:
            self._original_mac = self._get_current_mac(ap_interface)
            mac_address = create_mac_address(character)
            if not self._set_mac_address(mac_address):
                mac_address = None  # Failed to set, will use default
            else:
                mac_address = format_mac(mac_address)

            if not char_name:
                char_name = character.name

        # Bring interface up
        self._run_command(f"ip link set {ap_interface} up")

        # Configure IP
        self._configure_interface()

        # Create config files
        self._hostapd_config = self._create_hostapd_config(ssid)
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
            raise RuntimeError(f"hostapd failed to start: {stderr.decode()}")

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

        # Stop processes
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
        """Check if hotspot is currently running."""
        return bool(self._hostapd_process and self._hostapd_process.poll() is None)

    def restart(self, new_config: Optional[HotSpotchiConfig] = None) -> HotspotState:
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

    def update_config(self, new_config: HotSpotchiConfig) -> None:
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

        ssid, special_char = resolve_ssid(self.config)
        character = select_character(self.config)
        mac_address = format_mac(create_mac_address(character)) if character else None
        char_name = special_char or (character.name if character else None)

        return HotspotState(
            running=True,
            ssid=ssid,
            mac_address=mac_address,
            character_name=char_name,
            ip_address=self.config.ap_ip,
            hostapd_pid=self._hostapd_process.pid if self._hostapd_process else None,
            dnsmasq_pid=self._dnsmasq_process.pid if self._dnsmasq_process else None,
        )


def run_hotspot(config: HotSpotchiConfig) -> None:
    """Run the hotspot until interrupted.

    This is the main entry point for running HotSpotchi as a service.

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
        print("HotSpotchi is running!")
        print(f"  SSID: {state.ssid}")
        print(f"  MAC: {state.mac_address or 'default'}")
        print(f"  Character: {state.character_name or 'none'}")
        print(f"  IP: {state.ip_address}")
        print("\nPress Ctrl+C to stop")

        while manager.is_running():
            time.sleep(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        manager.stop()
        sys.exit(1)
