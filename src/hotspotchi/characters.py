"""
Character data for HotSpotchi.

Contains all MAC-based characters and special SSID-based event characters
for Tamagotchi Uni's Tama Search feature.

Characters are loaded from data/characters.yaml for easy customization.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Character:
    """A MAC-based Tamagotchi character.

    Attributes:
        byte1: First character byte (determines character with byte2)
        byte2: Second character byte
        name: Display name of the character
        season: Optional season restriction ("spring", "summer", "fall", "winter")
    """

    byte1: int
    byte2: int
    name: str
    season: str | None = None

    def __post_init__(self) -> None:
        """Validate byte values are in valid range."""
        if not (0 <= self.byte1 <= 255 and 0 <= self.byte2 <= 255):
            raise ValueError(f"Byte values must be 0-255, got {self.byte1}, {self.byte2}")


@dataclass(frozen=True)
class SpecialSSID:
    """A special SSID-based event character.

    These characters are triggered by broadcasting a specific WiFi network name (SSID)
    rather than by MAC address.

    Attributes:
        ssid: The exact SSID string to broadcast
        character_name: Name of the character that appears
        notes: Description of where/when this SSID was available
        active: Whether this SSID is still functional (some are deactivated in updates)
    """

    ssid: str
    character_name: str
    notes: str
    active: bool = True


def _parse_byte(value: int | str) -> int:
    """Parse a byte value from YAML (handles hex strings like '0x00')."""
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.startswith("0x"):
        return int(value, 16)
    return int(value)


def _load_characters_from_yaml() -> tuple[tuple[Character, ...], tuple[SpecialSSID, ...]]:
    """Load characters from the YAML data file.

    Returns:
        Tuple of (characters, special_ssids)
    """
    # Find the YAML file relative to this module
    data_file = Path(__file__).parent / "data" / "characters.yaml"

    if not data_file.exists():
        # Fallback to empty if file doesn't exist (shouldn't happen in production)
        return ((), ())

    with open(data_file) as f:
        data = yaml.safe_load(f)

    # Parse characters
    characters = []
    for char_data in data.get("characters", []):
        characters.append(
            Character(
                byte1=_parse_byte(char_data["byte1"]),
                byte2=_parse_byte(char_data["byte2"]),
                name=char_data["name"],
                season=char_data.get("season"),
            )
        )

    # Parse special SSIDs
    special_ssids = []
    for ssid_data in data.get("special_ssids", []):
        special_ssids.append(
            SpecialSSID(
                ssid=ssid_data["ssid"],
                character_name=ssid_data["character_name"],
                notes=ssid_data["notes"],
                active=ssid_data.get("active", True),
            )
        )

    return (tuple(characters), tuple(special_ssids))


# Load characters at module import time
CHARACTERS, SPECIAL_SSIDS = _load_characters_from_yaml()


def get_character_by_name(name: str) -> Character | None:
    """Find a character by name (case-insensitive).

    Args:
        name: Character name to search for

    Returns:
        Character if found, None otherwise
    """
    name_lower = name.lower()
    for char in CHARACTERS:
        if char.name.lower() == name_lower:
            return char
    return None


def get_character_by_bytes(byte1: int, byte2: int) -> Character | None:
    """Find a character by its byte values.

    Args:
        byte1: First byte value
        byte2: Second byte value

    Returns:
        Character if found, None otherwise
    """
    for char in CHARACTERS:
        if char.byte1 == byte1 and char.byte2 == byte2:
            return char
    return None


def get_seasonal_characters(season: str) -> list[Character]:
    """Get all characters for a specific season.

    Args:
        season: One of "spring", "summer", "fall", "winter"

    Returns:
        List of characters available in that season
    """
    return [char for char in CHARACTERS if char.season == season.lower()]


def get_active_special_ssids() -> list[SpecialSSID]:
    """Get all currently active special SSIDs.

    Returns:
        List of special SSIDs that are still functional
    """
    return [ssid for ssid in SPECIAL_SSIDS if ssid.active]
