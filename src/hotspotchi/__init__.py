"""
HotSpotchi - Tamagotchi Uni WiFi Hotspot

Create WiFi access points with custom MAC addresses and SSIDs
for meeting characters in Tamagotchi Uni's Tama Search feature.
"""

__version__ = "2.0.0"
__author__ = "HotSpotchi Contributors"

from hotspotchi.characters import CHARACTERS, SPECIAL_SSIDS, Character, SpecialSSID
from hotspotchi.config import HotSpotchiConfig, MacMode, SsidMode
from hotspotchi.mac import create_mac_address, format_mac
from hotspotchi.selection import select_character
from hotspotchi.ssid import resolve_ssid

__all__ = [
    # Version
    "__version__",
    # Characters
    "Character",
    "SpecialSSID",
    "CHARACTERS",
    "SPECIAL_SSIDS",
    # Config
    "HotSpotchiConfig",
    "MacMode",
    "SsidMode",
    # Functions
    "create_mac_address",
    "format_mac",
    "select_character",
    "resolve_ssid",
]
