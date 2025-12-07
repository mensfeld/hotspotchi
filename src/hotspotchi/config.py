"""
Configuration management for HotSpotchi.

Uses Pydantic for validated configuration with sensible defaults
for Raspberry Pi WiFi hotspot operation.
"""

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MacMode(str, Enum):
    """MAC address rotation mode.

    Determines how the MAC address (and thus character) is selected.
    """

    DAILY_RANDOM = "daily_random"
    """Different random character each day, same character all day."""

    RANDOM = "random"
    """New random character each time the service starts."""

    CYCLE = "cycle"
    """Cycle through all characters in order, one per start."""

    FIXED = "fixed"
    """Always use a specific character (set fixed_character_index)."""

    DISABLED = "disabled"
    """Don't change MAC address, use device default."""


class SsidMode(str, Enum):
    """SSID selection mode.

    Determines how the WiFi network name is set.
    """

    NORMAL = "normal"
    """Use the default SSID name (e.g., 'HotSpotchi')."""

    SPECIAL = "special"
    """Use a special event SSID to trigger exclusive characters."""

    CUSTOM = "custom"
    """Use a custom SSID name."""


class HotSpotchiConfig(BaseModel):
    """Main configuration for HotSpotchi.

    All settings have sensible defaults for typical Raspberry Pi use.
    Configuration can be loaded from environment variables with HOTSPOTCHI_ prefix.
    """

    # Network interface
    wifi_interface: str = Field(
        default="wlan0",
        description="WiFi interface to use for the access point",
    )

    # Concurrent mode - run AP alongside station connection
    concurrent_mode: bool = Field(
        default=False,
        description="Create virtual AP interface while staying connected to WiFi",
    )
    ap_interface: str = Field(
        default="uap0",
        description="Virtual AP interface name for concurrent mode",
    )

    # SSID configuration
    ssid_mode: SsidMode = Field(
        default=SsidMode.NORMAL,
        description="How to determine the network name",
    )
    default_ssid: str = Field(
        default="HotSpotchi",
        description="Default network name for normal mode",
    )
    custom_ssid: Optional[str] = Field(
        default=None,
        description="Custom network name for custom mode",
    )
    special_ssid_index: int = Field(
        default=0,
        ge=0,
        description="Index into SPECIAL_SSIDS list for special mode",
    )

    # MAC/Character configuration
    mac_mode: MacMode = Field(
        default=MacMode.DAILY_RANDOM,
        description="How to select characters",
    )
    fixed_character_index: int = Field(
        default=0,
        ge=0,
        description="Character index for fixed mode",
    )
    cycle_file: Path = Field(
        default=Path("/tmp/hotspotchi_cycle.txt"),
        description="File to persist cycle position",
    )
    include_special_ssids: bool = Field(
        default=True,
        description="Include special SSID characters in random/cycle rotation",
    )

    # Security - password prevents unwanted connections
    # Tamagotchi only needs to detect the SSID, not connect
    # None = generate random daily password (default, recommended)
    # Empty string = open network (not recommended)
    # Any string = use that fixed password
    wifi_password: Optional[str] = Field(
        default=None,
        description="WiFi password (WPA2). None=daily random, ''=open, or set fixed password",
    )

    # Network configuration
    ap_ip: str = Field(
        default="192.168.4.1",
        description="IP address for the access point",
    )
    ap_netmask: str = Field(
        default="255.255.255.0",
        description="Netmask for the access point network",
    )
    dhcp_range_start: str = Field(
        default="192.168.4.10",
        description="Start of DHCP range",
    )
    dhcp_range_end: str = Field(
        default="192.168.4.50",
        description="End of DHCP range",
    )

    # Web server
    web_host: str = Field(
        default="0.0.0.0",
        description="Host for web server to bind to",
    )
    web_port: int = Field(
        default=8080,
        ge=1,
        le=65535,
        description="Port for web server",
    )

    model_config = {
        "extra": "ignore",
    }

    @field_validator("wifi_password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        """Validate WiFi password meets WPA2 requirements."""
        # None = daily random password (valid)
        # Empty string = open network (valid but not recommended)
        # Non-empty string = must be at least 8 chars for WPA2
        if v is not None and v != "" and len(v) < 8:
            raise ValueError("WiFi password must be at least 8 characters for WPA2")
        return v

    @field_validator("custom_ssid")
    @classmethod
    def validate_ssid(cls, v: Optional[str]) -> Optional[str]:
        """Validate SSID length."""
        if v is not None and len(v) > 32:
            raise ValueError("SSID cannot exceed 32 characters")
        return v

    def get_effective_ssid(self) -> str:
        """Get the SSID that will actually be used based on mode.

        Returns:
            The SSID string to broadcast
        """
        if self.ssid_mode == SsidMode.CUSTOM and self.custom_ssid:
            return self.custom_ssid
        if self.ssid_mode == SsidMode.SPECIAL:
            from hotspotchi.characters import SPECIAL_SSIDS

            if 0 <= self.special_ssid_index < len(SPECIAL_SSIDS):
                return SPECIAL_SSIDS[self.special_ssid_index].ssid
        return self.default_ssid


def load_config(config_path: Optional[Path] = None) -> HotSpotchiConfig:
    """Load configuration from file and/or environment.

    Args:
        config_path: Optional path to YAML config file

    Returns:
        Validated configuration object
    """
    if config_path and config_path.exists():
        import yaml

        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return HotSpotchiConfig(**data)

    return HotSpotchiConfig()


def save_config(config: HotSpotchiConfig, config_path: Path) -> None:
    """Save configuration to YAML file.

    Args:
        config: Configuration to save
        config_path: Path to write config file
    """
    import yaml

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.safe_dump(config.model_dump(), f, default_flow_style=False)
