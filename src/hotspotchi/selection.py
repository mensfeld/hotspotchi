"""
Character selection logic for HotSpotchi.

Implements all five character selection modes:
- daily_random: Same random character all day
- random: New random character each call
- cycle: Progress through characters in order
- fixed: Always use specific character
- disabled: No character selection

When include_special_ssids is enabled, special SSID characters
are included in the rotation pool alongside MAC-based characters.
"""

import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from hotspotchi.characters import CHARACTERS, SPECIAL_SSIDS, Character, SpecialSSID
from hotspotchi.config import HotSpotchiConfig, MacMode
from hotspotchi.exclusions import get_exclusion_manager


@dataclass
class SelectionResult:
    """Result of character selection.

    Can be either a MAC-based character or a special SSID character.
    """

    character: Optional[Character] = None
    special_ssid: Optional[SpecialSSID] = None

    @property
    def name(self) -> Optional[str]:
        """Get the character name."""
        if self.special_ssid:
            return self.special_ssid.character_name
        if self.character:
            return self.character.name
        return None

    @property
    def is_special_ssid(self) -> bool:
        """Check if this is a special SSID selection."""
        return self.special_ssid is not None

    @property
    def ssid(self) -> Optional[str]:
        """Get the SSID if this is a special SSID selection."""
        if self.special_ssid:
            return self.special_ssid.ssid
        return None


def get_day_number(date: Optional[datetime] = None) -> int:
    """Calculate a unique number for a given day.

    This provides a deterministic seed for daily random selection,
    ensuring the same character appears all day but changes at midnight.

    The formula (year * 366 + month * 31 + day) guarantees unique
    values for each day while being simple to compute.

    Args:
        date: Date to calculate for (defaults to now)

    Returns:
        Unique integer for the given day
    """
    if date is None:
        date = datetime.now()
    return date.year * 366 + date.month * 31 + date.day


def get_available_characters(
    characters: tuple[Character, ...] = CHARACTERS,
    respect_exclusions: bool = True,
) -> tuple[Character, ...]:
    """Get characters that are available for selection.

    Filters out excluded characters if respect_exclusions is True.

    Args:
        characters: Full tuple of characters
        respect_exclusions: If True, filter out excluded characters

    Returns:
        Tuple of available characters
    """
    if not respect_exclusions:
        return characters

    exclusion_manager = get_exclusion_manager()
    available = []
    for i, char in enumerate(characters):
        if not exclusion_manager.is_excluded(i):
            available.append(char)

    return tuple(available) if available else characters  # Fallback to all if all excluded


def get_cycle_index(cycle_file: Path, total_characters: int) -> int:
    """Get the current cycle index and increment it for next time.

    The cycle index is persisted to disk so it survives reboots
    and continues from where it left off.

    Args:
        cycle_file: Path to file storing the current index
        total_characters: Total number of characters to cycle through

    Returns:
        Current cycle index (0-based)
    """
    # Read current index
    try:
        index = int(cycle_file.read_text().strip())
    except (FileNotFoundError, ValueError):
        index = 0

    # Ensure index is valid
    index = index % total_characters

    # Save next index for next time
    next_index = (index + 1) % total_characters
    try:
        cycle_file.parent.mkdir(parents=True, exist_ok=True)
        cycle_file.write_text(str(next_index))
    except OSError:
        pass  # Best effort - continue even if we can't persist

    return index


def select_character(
    config: HotSpotchiConfig,
    characters: tuple[Character, ...] = CHARACTERS,
    current_date: Optional[datetime] = None,
    respect_exclusions: bool = True,
) -> Optional[Character]:
    """Select a character based on the configured MAC mode.

    Args:
        config: Configuration with mac_mode and related settings
        characters: Tuple of available characters (defaults to all)
        current_date: Override current date (for testing)
        respect_exclusions: If True, excluded characters won't be selected
            (except in fixed mode where the user explicitly chooses)

    Returns:
        Selected Character, or None if mode is DISABLED
    """
    if not characters:
        return None

    if config.mac_mode == MacMode.DISABLED:
        return None

    # Fixed mode ignores exclusions - user explicitly chose this character
    if config.mac_mode == MacMode.FIXED:
        # Clamp index to valid range
        index = min(config.fixed_character_index, len(characters) - 1)
        index = max(0, index)
        return characters[index]

    # For rotation modes, filter out excluded characters
    available = get_available_characters(characters, respect_exclusions)
    if not available:
        return None

    if config.mac_mode == MacMode.DAILY_RANDOM:
        day = get_day_number(current_date)
        random.seed(day)
        return random.choice(available)

    if config.mac_mode == MacMode.RANDOM:
        return random.choice(available)

    if config.mac_mode == MacMode.CYCLE:
        index = get_cycle_index(config.cycle_file, len(available))
        return available[index]

    return None


def get_active_special_ssids(respect_exclusions: bool = True) -> list[tuple[int, SpecialSSID]]:
    """Get all active special SSIDs with their indices.

    Args:
        respect_exclusions: If True, filter out excluded SSIDs

    Returns:
        List of (index, SpecialSSID) tuples
    """
    exclusion_manager = get_exclusion_manager()
    result = []
    for i, ssid in enumerate(SPECIAL_SSIDS):
        if not ssid.active:
            continue
        if respect_exclusions and exclusion_manager.is_ssid_excluded(i):
            continue
        result.append((i, ssid))
    return result


def select_combined(
    config: HotSpotchiConfig,
    current_date: Optional[datetime] = None,
    respect_exclusions: bool = True,
) -> SelectionResult:
    """Select a character from the combined pool of MAC and special SSID characters.

    When config.include_special_ssids is True, special SSIDs are included in the
    random/daily_random/cycle rotation. When a special SSID is selected, the
    result will have is_special_ssid=True and provide the special SSID name.

    Args:
        config: Configuration with mac_mode and related settings
        current_date: Override current date (for testing)
        respect_exclusions: If True, excluded characters won't be selected

    Returns:
        SelectionResult containing either a Character or SpecialSSID
    """
    if config.mac_mode == MacMode.DISABLED:
        return SelectionResult()

    # Fixed mode - just use the regular character selection
    if config.mac_mode == MacMode.FIXED:
        char = select_character(config, CHARACTERS, current_date, respect_exclusions)
        return SelectionResult(character=char)

    # Get available MAC characters
    available_chars = list(get_available_characters(CHARACTERS, respect_exclusions))

    # Get active special SSIDs if enabled (respecting exclusions)
    special_ssid_items: list[tuple[int, SpecialSSID]] = []
    if config.include_special_ssids:
        special_ssid_items = get_active_special_ssids(respect_exclusions)

    # Build combined pool: MAC characters first, then special SSIDs
    total_count = len(available_chars) + len(special_ssid_items)

    if total_count == 0:
        return SelectionResult()

    # Select an index from the combined pool
    if config.mac_mode == MacMode.DAILY_RANDOM:
        day = get_day_number(current_date)
        random.seed(day)
        selected_index = random.randint(0, total_count - 1)
    elif config.mac_mode == MacMode.RANDOM:
        selected_index = random.randint(0, total_count - 1)
    elif config.mac_mode == MacMode.CYCLE:
        selected_index = get_cycle_index(config.cycle_file, total_count)
    else:
        return SelectionResult()

    # Determine if it's a MAC character or special SSID
    if selected_index < len(available_chars):
        return SelectionResult(character=available_chars[selected_index])
    else:
        ssid_index = selected_index - len(available_chars)
        _, ssid = special_ssid_items[ssid_index]
        return SelectionResult(special_ssid=ssid)


def get_next_character(
    config: HotSpotchiConfig,
    characters: tuple[Character, ...] = CHARACTERS,
) -> Optional[Character]:
    """Preview the next character without advancing state.

    Useful for showing what character will appear next in cycle mode.

    Args:
        config: Configuration with mac_mode and related settings
        characters: Tuple of available characters

    Returns:
        Next character that would be selected, or None
    """
    if config.mac_mode != MacMode.CYCLE:
        return None

    try:
        current_index = int(config.cycle_file.read_text().strip())
    except (FileNotFoundError, ValueError):
        current_index = 0

    current_index = current_index % len(characters)
    return characters[current_index]


def get_upcoming_characters(
    config: HotSpotchiConfig,
    count: int = 7,
    characters: tuple[Character, ...] = CHARACTERS,
) -> list[Character]:
    """Get a list of upcoming characters for cycle mode.

    Args:
        config: Configuration with mac_mode and related settings
        count: Number of upcoming characters to return
        characters: Tuple of available characters

    Returns:
        List of characters in order they will appear
    """
    if config.mac_mode != MacMode.CYCLE:
        return []

    try:
        current_index = int(config.cycle_file.read_text().strip())
    except (FileNotFoundError, ValueError):
        current_index = 0

    upcoming = []
    for i in range(count):
        idx = (current_index + i) % len(characters)
        upcoming.append(characters[idx])

    return upcoming


def get_seconds_until_midnight() -> int:
    """Calculate seconds remaining until midnight.

    Useful for countdown display in daily_random mode.

    Returns:
        Number of seconds until next day starts
    """
    now = datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # Add one day to get next midnight
    from datetime import timedelta

    next_midnight = midnight + timedelta(days=1)
    delta = next_midnight - now
    return int(delta.total_seconds())


def generate_daily_password(current_date: Optional[datetime] = None) -> str:
    """Generate a random WPA2 password that changes daily.

    Uses the same deterministic daily seed as character selection,
    ensuring the password is consistent throughout the day but
    changes at midnight. The password is 16 characters long,
    using alphanumeric characters for WPA2 compatibility.

    Args:
        current_date: Override current date (for testing)

    Returns:
        16-character random password
    """
    import string

    day = get_day_number(current_date)
    # Use a different seed offset to avoid correlation with character selection
    random.seed(day + 0x7A6DA0)  # "TAMA" signature offset

    # WPA2-safe characters (alphanumeric)
    chars = string.ascii_letters + string.digits
    password = "".join(random.choice(chars) for _ in range(16))

    return password
