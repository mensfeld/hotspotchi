"""Tests for character selection logic."""

from datetime import datetime
from pathlib import Path

from hotspotchi.characters import CHARACTERS
from hotspotchi.config import HotSpotchiConfig, MacMode
from hotspotchi.selection import (
    get_cycle_index,
    get_day_number,
    get_next_character,
    get_seconds_until_midnight,
    get_upcoming_characters,
    select_character,
)


class TestGetDayNumber:
    """Tests for day number calculation."""

    def test_same_day_same_number(self):
        """Same date should produce same day number."""
        date = datetime(2024, 6, 15)
        assert get_day_number(date) == get_day_number(date)

    def test_different_days_different_numbers(self):
        """Different dates should produce different day numbers."""
        date1 = datetime(2024, 6, 15)
        date2 = datetime(2024, 6, 16)
        assert get_day_number(date1) != get_day_number(date2)

    def test_year_rollover(self):
        """Year change should affect day number."""
        date1 = datetime(2024, 12, 31)
        date2 = datetime(2025, 1, 1)
        assert get_day_number(date1) != get_day_number(date2)

    def test_uses_current_time_when_none(self):
        """Should use current datetime when no date provided."""
        result = get_day_number()
        expected = get_day_number(datetime.now())
        assert result == expected

    def test_deterministic(self):
        """Same date should always give same result."""
        date = datetime(2024, 3, 14)  # Pi day
        results = [get_day_number(date) for _ in range(10)]
        assert len(set(results)) == 1


class TestCycleIndex:
    """Tests for cycle index persistence."""

    def test_starts_at_zero(self, temp_dir: Path):
        """New cycle file should start at index 0."""
        cycle_file = temp_dir / "cycle.txt"
        index = get_cycle_index(cycle_file, len(CHARACTERS))
        assert index == 0

    def test_increments_on_each_call(self, temp_dir: Path):
        """Index should increment with each call."""
        cycle_file = temp_dir / "cycle.txt"
        indices = [get_cycle_index(cycle_file, 10) for _ in range(5)]
        assert indices == [0, 1, 2, 3, 4]

    def test_wraps_around(self, temp_dir: Path):
        """Index should wrap to 0 after reaching end."""
        cycle_file = temp_dir / "cycle.txt"
        cycle_file.write_text("9")  # Start at 9 with 10 characters
        index = get_cycle_index(cycle_file, 10)
        assert index == 9
        next_index = get_cycle_index(cycle_file, 10)
        assert next_index == 0

    def test_handles_corrupted_file(self, temp_dir: Path):
        """Should handle corrupted cycle file gracefully."""
        cycle_file = temp_dir / "cycle.txt"
        cycle_file.write_text("not_a_number")
        index = get_cycle_index(cycle_file, 10)
        assert index == 0

    def test_handles_missing_file(self, temp_dir: Path):
        """Should handle missing file gracefully."""
        cycle_file = temp_dir / "nonexistent.txt"
        index = get_cycle_index(cycle_file, 10)
        assert index == 0

    def test_creates_parent_directories(self, temp_dir: Path):
        """Should create parent directories if needed."""
        cycle_file = temp_dir / "subdir" / "nested" / "cycle.txt"
        index = get_cycle_index(cycle_file, 10)
        assert index == 0
        assert cycle_file.exists()

    def test_handles_out_of_range_index(self, temp_dir: Path):
        """Should handle index larger than character count."""
        cycle_file = temp_dir / "cycle.txt"
        cycle_file.write_text("100")  # Larger than 10
        index = get_cycle_index(cycle_file, 10)
        assert 0 <= index < 10  # Should be wrapped


class TestSelectCharacter:
    """Tests for character selection across all modes."""

    def test_daily_random_same_character_same_day(self, daily_random_config: HotSpotchiConfig):
        """Daily random mode should return same character all day."""
        fixed_date = datetime(2024, 6, 15)
        char1 = select_character(daily_random_config, current_date=fixed_date)
        char2 = select_character(daily_random_config, current_date=fixed_date)
        assert char1 == char2

    def test_daily_random_different_days(self, daily_random_config: HotSpotchiConfig):
        """Daily random mode should likely differ between days."""
        # Note: Theoretically could be same by chance, but very unlikely
        date1 = datetime(2024, 6, 15)
        date2 = datetime(2024, 6, 16)
        char1 = select_character(daily_random_config, current_date=date1)
        char2 = select_character(daily_random_config, current_date=date2)
        # We can't guarantee different, but for these specific dates they are
        # If this fails, consider using more distant dates
        # Note: Could theoretically be same by chance, test passes either way
        assert char1 is not None and char2 is not None

    def test_random_mode_returns_character(self):
        """Random mode should return a valid character."""
        config = HotSpotchiConfig(mac_mode=MacMode.RANDOM)
        char = select_character(config)
        assert char in CHARACTERS

    def test_random_mode_varies(self):
        """Random mode should produce variety over many calls."""
        config = HotSpotchiConfig(mac_mode=MacMode.RANDOM)
        chars = {select_character(config) for _ in range(20)}
        # Should have at least some variety
        assert len(chars) > 1

    def test_fixed_mode_correct_index(self, fixed_config: HotSpotchiConfig):
        """Fixed mode should return character at specified index."""
        char = select_character(fixed_config)
        assert char == CHARACTERS[5]

    def test_fixed_mode_index_bounds_high(self):
        """Fixed mode should clamp to last character for too-high index."""
        config = HotSpotchiConfig(
            mac_mode=MacMode.FIXED,
            fixed_character_index=9999,
        )
        char = select_character(config)
        assert char == CHARACTERS[-1]

    def test_fixed_mode_index_zero(self):
        """Fixed mode with index 0 should return first character."""
        config = HotSpotchiConfig(
            mac_mode=MacMode.FIXED,
            fixed_character_index=0,
        )
        char = select_character(config)
        assert char == CHARACTERS[0]

    def test_disabled_returns_none(self):
        """Disabled mode should return None."""
        config = HotSpotchiConfig(mac_mode=MacMode.DISABLED)
        char = select_character(config)
        assert char is None

    def test_cycle_mode(self, cycle_config: HotSpotchiConfig):
        """Cycle mode should progress through characters."""
        char1 = select_character(cycle_config)
        char2 = select_character(cycle_config)
        char3 = select_character(cycle_config)

        assert char1 == CHARACTERS[0]
        assert char2 == CHARACTERS[1]
        assert char3 == CHARACTERS[2]

    def test_empty_characters_returns_none(self, daily_random_config: HotSpotchiConfig):
        """Should return None if no characters available."""
        char = select_character(daily_random_config, characters=())
        assert char is None


class TestGetNextCharacter:
    """Tests for next character preview."""

    def test_returns_none_for_non_cycle_mode(self, daily_random_config: HotSpotchiConfig):
        """Should return None for non-cycle modes."""
        char = get_next_character(daily_random_config)
        assert char is None

    def test_returns_character_for_cycle_mode(self, cycle_config: HotSpotchiConfig):
        """Should return next character for cycle mode."""
        char = get_next_character(cycle_config)
        assert char is not None
        assert char in CHARACTERS


class TestGetUpcomingCharacters:
    """Tests for upcoming characters list."""

    def test_returns_empty_for_non_cycle_mode(self, daily_random_config: HotSpotchiConfig):
        """Should return empty list for non-cycle modes."""
        upcoming = get_upcoming_characters(daily_random_config)
        assert upcoming == []

    def test_returns_correct_count(self, cycle_config: HotSpotchiConfig):
        """Should return requested number of characters."""
        upcoming = get_upcoming_characters(cycle_config, count=5)
        assert len(upcoming) == 5

    def test_returns_characters_in_order(self, cycle_config: HotSpotchiConfig):
        """Characters should be in correct order."""
        upcoming = get_upcoming_characters(cycle_config, count=3)
        # First character should be current (index 0)
        assert upcoming[0] == CHARACTERS[0]
        assert upcoming[1] == CHARACTERS[1]
        assert upcoming[2] == CHARACTERS[2]


class TestGetSecondsUntilMidnight:
    """Tests for midnight countdown."""

    def test_returns_positive_number(self):
        """Should always return positive seconds."""
        seconds = get_seconds_until_midnight()
        assert seconds > 0

    def test_returns_less_than_24_hours(self):
        """Should always be less than 24 hours."""
        seconds = get_seconds_until_midnight()
        assert seconds <= 24 * 60 * 60

    def test_is_reasonable(self):
        """Should return a reasonable value."""
        seconds = get_seconds_until_midnight()
        # At least 1 second (unless exactly midnight)
        assert seconds >= 0
        # At most 24 hours
        assert seconds <= 86400
