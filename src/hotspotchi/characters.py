"""
Character data for HotSpotchi.

Contains all MAC-based characters and special SSID-based event characters
for Tamagotchi Uni's Tama Search feature.
"""

from dataclasses import dataclass
from typing import Optional


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
    season: Optional[str] = None

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


# ============================================
# NORMAL CHARACTERS (MAC address based)
# ============================================
# The final two bytes of the MAC address determine which character appears.
# MAC format: 02:7A:6D:A0:XX:YY where XX=byte1, YY=byte2

CHARACTERS: tuple[Character, ...] = (
    # Common characters (available year-round)
    Character(0x00, 0x00, "Mametchi"),
    Character(0x00, 0x10, "Weeptchi"),
    Character(0x00, 0x20, "Hypertchi"),
    Character(0x00, 0x30, "Kuchipatchi"),
    Character(0x00, 0x40, "Shykutchi"),
    Character(0x00, 0x50, "Bigsmile"),
    Character(0x00, 0x60, "Kikitchi"),
    Character(0x00, 0x70, "Simagurutchi"),
    Character(0x00, 0x80, "Gozarutchi"),
    Character(0x00, 0x90, "Milktchi"),
    Character(0x00, 0xA0, "Mimitchi"),
    Character(0x00, 0xB0, "Picochutchi"),
    Character(0x00, 0xC0, "Memetchi"),
    Character(0x00, 0xD0, "Bubbletchi"),
    Character(0x00, 0xE0, "Woopatchi"),
    Character(0x00, 0xF0, "Neliatchi"),
    Character(0x01, 0x00, "Sebiretchi"),
    Character(0x01, 0x10, "Momotchi"),
    Character(0x01, 0x20, "Unimarutchi"),
    Character(0x01, 0x30, "Simasimatchi"),
    Character(0x01, 0x40, "Yattatchi"),
    Character(0x01, 0x50, "Nazotchi"),
    Character(0x01, 0x60, "Maidtchi"),
    Character(0x01, 0x70, "Uwasatchi"),
    Character(0x01, 0x80, "Shirimotchi"),
    Character(0x01, 0x90, "Chukatchi"),
    Character(0x01, 0xA0, "Watawatatchi"),
    Character(0x01, 0xB0, "Crayontchi"),
    Character(0x01, 0xC0, "Pierrotchi"),
    Character(0x01, 0xD0, "Majokkotchi"),
    Character(0x01, 0xE0, "Hatakemotchi"),
    Character(0x01, 0xF0, "Butterflytchi"),
    Character(0x02, 0x00, "Attendant"),
    Character(0x02, 0x10, "Maskutchi"),
    Character(0x02, 0x20, "Ichirinshatchi"),
    Character(0x02, 0x30, "Nonopotchi"),
    Character(0x02, 0x40, "Himebaratchi"),
    Character(0x02, 0x50, "Pichipitchi"),
    Character(0x02, 0x60, "Youmotchi"),
    Character(0x02, 0x70, "Fairytchi"),
    Character(0x02, 0x80, "Majoritchi"),
    Character(0x02, 0x90, "Madamtchi"),
    Character(0x02, 0xA0, "Lovesolatchi"),
    Character(0x02, 0xB0, "Miraitchi"),
    Character(0x02, 0xC0, "Clulutchi"),
    Character(0x02, 0xD0, "Morijikatchi"),
    Character(0x02, 0xE0, "Guriguritchi"),
    Character(0x02, 0xF0, "Sunopotchi"),
    Character(0x03, 0x00, "Rinkurutchi"),
    Character(0x03, 0x10, "Oyajitchi"),
    Character(0x03, 0x20, "Charatchi"),
    Character(0x03, 0x30, "Ninjanyatchi"),
    Character(0x03, 0x40, "Paintotchi"),
    # Seasonal characters - set your Tamagotchi's date to the right season!
    # Spring (March-May)
    Character(0x00, 0x0F, "Rosetchi", season="spring"),
    Character(0x01, 0x0F, "Yotsubatchi", season="spring"),
    Character(0x02, 0x0F, "Hanafuwatchi", season="spring"),
    Character(0x03, 0x0F, "Musiharutchi", season="spring"),
    # Summer (June-August)
    Character(0x00, 0x1F, "Soyofuwatchi", season="summer"),
    Character(0x01, 0x1F, "Hyurutchi", season="summer"),
    Character(0x02, 0x1F, "Kiramotchi", season="summer"),
    Character(0x03, 0x1F, "Awawatchi", season="summer"),
    # Fall (September-November)
    Character(0x00, 0x2F, "Momijitchi", season="fall"),
    Character(0x01, 0x2F, "Chestnut Angel", season="fall"),
    Character(0x02, 0x2F, "Ginkgotchi", season="fall"),
    Character(0x03, 0x2F, "Kinokotchi", season="fall"),
    # Winter (December-February)
    Character(0x00, 0x3F, "Yukinkotchi", season="winter"),
    Character(0x01, 0x3F, "Snowboytchi", season="winter"),
    Character(0x02, 0x3F, "Fuyukotchi", season="winter"),
    Character(0x03, 0x3F, "Yuki Onna", season="winter"),
)

# ============================================
# SPECIAL CHARACTERS (SSID-based)
# ============================================
# These are triggered by the WiFi network NAME, not MAC address.
# Originally exclusive to specific events/locations in Japan.

SPECIAL_SSIDS: tuple[SpecialSSID, ...] = (
    # World Tour & Event Exclusives
    SpecialSSID(
        ssid="FyKHSZlwQCzTpGuDHrJclhA2Kq9vYNdP",
        character_name="Angel & Devil",
        notes="World Tamagotchi Tour event spots",
    ),
    # Bandai Cross Store Exclusives
    SpecialSSID(
        ssid="oHWqLZuDba3HjCwemPXc61et9lKpDE60",
        character_name="Makiko",
        notes="Bandai Cross stores",
    ),
    SpecialSSID(
        ssid="TtKihQXLtUvf8Pg4pPfzgZNm3cMifPW2",
        character_name="Snowmarutchi",
        notes="Bandai Cross stores",
    ),
    SpecialSSID(
        ssid="BS5nm6JYUGABKZKGFNWEpMM7Vag4qUeB",
        character_name="Manekimimitchi",
        notes="Bandai Cross stores",
    ),
    # Bandai Namco Cross Store Regional Exclusives
    SpecialSSID(
        ssid="n1ngVgVtJ6Q4l7HZ3RLbAKI7KdkByZLa",
        character_name="MasamunePatchi",
        notes="Bandai Namco Cross Store - Sendai",
    ),
    SpecialSSID(
        ssid="S0ccc5tmCxe69la0ff9UEBVy42gDzirG",
        character_name="GirlyMametchi",
        notes="Bandai Namco Cross Store - Koshigaya/Tokyo/SHIBUYA109/Yokohama",
    ),
    SpecialSSID(
        ssid="XqCIzP70WUOOgmuYJyN71bn39PmOhRXS",
        character_name="WaiterMametchi",
        notes="Bandai Namco Cross Store - Nagoya",
    ),
    SpecialSSID(
        ssid="bDwg0TAt3bFJvrBUd9Zh4Z71cJ9NbihX",
        character_name="MomKuchipatchi",
        notes="Bandai Namco Cross Store - Osaka Umeda",
    ),
    SpecialSSID(
        ssid="4lcA42klr3UlQh3iPafHggFuHwNmQDkA",
        character_name="MentaiMametchi",
        notes="Bandai Namco Cross Store - Hakata",
    ),
    # Pop-up Store & Event Exclusives
    SpecialSSID(
        ssid="r71676YmaL7BgMqjQwoU9SVuZGDMRDLK",
        character_name="Youngmametchi",
        notes="Gather, Everyone! Tamagotchi Shop pop-up - Japan",
    ),
    SpecialSSID(
        ssid="cK4zCzlkZRZZRhQgVev42ghANdfscPGx",
        character_name="1123 Mametchi",
        notes="Celebrating 28 Years! Tamagotchi Birthday! - Harajuku Harakado",
    ),
    SpecialSSID(
        ssid="eczNNK2nzEKFuGQuBcf8UvKymLhBFeTQ",
        character_name="atre Memetchi",
        notes="atre x Tamagotchi atre WINTER CARNIVAL event",
    ),
    SpecialSSID(
        ssid="pQYeFibtVXgJhOtNgDOEXC5ygkjkpJKC",
        character_name="Pochitchi",
        notes="Tamagotchi Shop stores",
    ),
    SpecialSSID(
        ssid="gCjUrU3DwNsjpIWsh53bDAI2g72KoxL8",
        character_name="Asa&Yorutchi",
        notes="Tamagotchi X PokoPea pop up store",
    ),
    SpecialSSID(
        ssid="1xuULYofy8K4yN6h0eCJpZ45qkKJH5cT",
        character_name="Tamako hime",
        notes="Capcom Cafe X Tamagotchi no Puchi Puchi Omisetchi",
    ),
    SpecialSSID(
        ssid="4w4AHuUMZw5IJ6n8sGCviXPzO1RZz16g",
        character_name="20th Yattatchi",
        notes="LACHIC 20th Anniversary X Tamagotchi event",
    ),
    SpecialSSID(
        ssid="YsDXsevVKDBK1f5xTed6XkYqUrCpazrQ",
        character_name="Factory Tama",
        notes="Tamagotchi Factory store",
    ),
    # Ciao/Ribon Events
    SpecialSSID(
        ssid="JuqfEv8zFn8LnJdkUfkCgBRU7YfVf9nG",
        character_name="Milktchi",
        notes="Ciao x Ribon Girls Comic Fest 2024",
    ),
    SpecialSSID(
        ssid="AYlvLBg6Ex8WoDdmk1AftZ5E3evPhYll",
        character_name="Yumemitchi",
        notes="Ciao x Ribon Girls Comic Fest 2024",
    ),
    SpecialSSID(
        ssid="QvWG15JJdsaqejxoNr0Iyc9PPtheRHFg",
        character_name="Tamahiko oji",
        notes="Ciao Summer Festival 2025",
    ),
    # Collaboration Events
    SpecialSSID(
        ssid="sleVMCdb7AuJJDNBj9CJD9CPPkKdGfib",
        character_name="M Hello Kitty",
        notes="Sanrio Puroland - INACTIVE as of v2.1.0",
        active=False,
    ),
)


def get_character_by_name(name: str) -> Optional[Character]:
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


def get_character_by_bytes(byte1: int, byte2: int) -> Optional[Character]:
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
