"""
SSID resolution logic for Hotspotchi.

Handles selection of WiFi network names (SSIDs) based on configuration,
including special event SSIDs that trigger exclusive characters.
"""

from hotspotchi.characters import SPECIAL_SSIDS, SpecialSSID
from hotspotchi.config import HotspotchiConfig, SsidMode


def resolve_ssid(config: HotspotchiConfig) -> tuple[str, str | None]:
    """Resolve the SSID to use based on configuration.

    Args:
        config: Configuration with ssid_mode and related settings

    Returns:
        Tuple of (ssid_name, character_name_or_none)
        character_name is set when using a special SSID
    """
    if config.ssid_mode == SsidMode.SPECIAL and SPECIAL_SSIDS:
        index = min(config.special_ssid_index, len(SPECIAL_SSIDS) - 1)
        index = max(0, index)
        special = SPECIAL_SSIDS[index]
        return special.ssid, special.character_name

    if config.ssid_mode == SsidMode.CUSTOM and config.custom_ssid:
        return config.custom_ssid, None

    # Default to normal mode
    return config.default_ssid, None


def find_ssid_by_character(character_name: str) -> SpecialSSID | None:
    """Find a special SSID by character name.

    Args:
        character_name: Name of the character to find

    Returns:
        SpecialSSID if found, None otherwise
    """
    name_lower = character_name.lower()
    for ssid in SPECIAL_SSIDS:
        if ssid.character_name.lower() == name_lower:
            return ssid
    return None


def find_ssid_by_ssid_string(ssid_string: str) -> SpecialSSID | None:
    """Find a special SSID by its SSID string.

    Args:
        ssid_string: The SSID string to search for

    Returns:
        SpecialSSID if found, None otherwise
    """
    for ssid in SPECIAL_SSIDS:
        if ssid.ssid == ssid_string:
            return ssid
    return None


def get_ssid_index(ssid_string: str) -> int | None:
    """Get the index of a special SSID.

    Useful for setting special_ssid_index in configuration.

    Args:
        ssid_string: The SSID string to find

    Returns:
        Index in SPECIAL_SSIDS if found, None otherwise
    """
    for i, ssid in enumerate(SPECIAL_SSIDS):
        if ssid.ssid == ssid_string:
            return i
    return None


def get_ssid_index_by_character(character_name: str) -> int | None:
    """Get the index of a special SSID by character name.

    Args:
        character_name: Name of the character

    Returns:
        Index in SPECIAL_SSIDS if found, None otherwise
    """
    name_lower = character_name.lower()
    for i, ssid in enumerate(SPECIAL_SSIDS):
        if ssid.character_name.lower() == name_lower:
            return i
    return None


def is_valid_ssid(ssid: str) -> bool:
    """Check if an SSID string is valid.

    SSIDs must be 1-32 characters and contain only valid characters.

    Args:
        ssid: SSID string to validate

    Returns:
        True if valid SSID
    """
    if not ssid or len(ssid) > 32:
        return False

    # SSID can contain most printable ASCII characters
    # but some characters may cause issues with certain devices
    return all(32 <= ord(c) <= 126 for c in ssid)


def list_special_ssids(active_only: bool = True) -> list[tuple[int, SpecialSSID]]:
    """List all special SSIDs with their indices.

    Args:
        active_only: If True, only return active SSIDs

    Returns:
        List of (index, SpecialSSID) tuples
    """
    result = []
    for i, ssid in enumerate(SPECIAL_SSIDS):
        if active_only and not ssid.active:
            continue
        result.append((i, ssid))
    return result
