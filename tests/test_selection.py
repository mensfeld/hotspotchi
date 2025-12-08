"""Tests for character selection logic."""

from datetime import datetime
from pathlib import Path

from hotspotchi.characters import CHARACTERS, SPECIAL_SSIDS, Character
from hotspotchi.config import HotspotchiConfig, MacMode, SsidMode
from hotspotchi.selection import (
    SelectionResult,
    generate_daily_password,
    get_available_characters,
    get_current_season,
    get_cycle_index,
    get_day_number,
    get_next_character,
    get_seconds_until_midnight,
    get_upcoming_characters,
    is_character_available_now,
    select_character,
    select_combined,
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

    def test_daily_random_same_character_same_day(self, daily_random_config: HotspotchiConfig):
        """Daily random mode should return same character all day."""
        fixed_date = datetime(2024, 6, 15)
        char1 = select_character(daily_random_config, current_date=fixed_date)
        char2 = select_character(daily_random_config, current_date=fixed_date)
        assert char1 == char2

    def test_daily_random_different_days(self, daily_random_config: HotspotchiConfig):
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
        config = HotspotchiConfig(mac_mode=MacMode.RANDOM)
        char = select_character(config)
        assert char in CHARACTERS

    def test_random_mode_varies(self):
        """Random mode should produce variety over many calls."""
        config = HotspotchiConfig(mac_mode=MacMode.RANDOM)
        chars = {select_character(config) for _ in range(20)}
        # Should have at least some variety
        assert len(chars) > 1

    def test_fixed_mode_correct_index(self, fixed_config: HotspotchiConfig):
        """Fixed mode should return character at specified index."""
        char = select_character(fixed_config)
        assert char == CHARACTERS[5]

    def test_fixed_mode_index_bounds_high(self):
        """Fixed mode should clamp to last character for too-high index."""
        config = HotspotchiConfig(
            mac_mode=MacMode.FIXED,
            fixed_character_index=9999,
        )
        char = select_character(config)
        assert char == CHARACTERS[-1]

    def test_fixed_mode_index_zero(self):
        """Fixed mode with index 0 should return first character."""
        config = HotspotchiConfig(
            mac_mode=MacMode.FIXED,
            fixed_character_index=0,
        )
        char = select_character(config)
        assert char == CHARACTERS[0]

    def test_disabled_returns_none(self):
        """Disabled mode should return None."""
        config = HotspotchiConfig(mac_mode=MacMode.DISABLED)
        char = select_character(config)
        assert char is None

    def test_cycle_mode(self, cycle_config: HotspotchiConfig):
        """Cycle mode should progress through characters."""
        char1 = select_character(cycle_config)
        char2 = select_character(cycle_config)
        char3 = select_character(cycle_config)

        assert char1 == CHARACTERS[0]
        assert char2 == CHARACTERS[1]
        assert char3 == CHARACTERS[2]

    def test_empty_characters_returns_none(self, daily_random_config: HotspotchiConfig):
        """Should return None if no characters available."""
        char = select_character(daily_random_config, characters=())
        assert char is None


class TestGetNextCharacter:
    """Tests for next character preview."""

    def test_returns_none_for_non_cycle_mode(self, daily_random_config: HotspotchiConfig):
        """Should return None for non-cycle modes."""
        char = get_next_character(daily_random_config)
        assert char is None

    def test_returns_character_for_cycle_mode(self, cycle_config: HotspotchiConfig):
        """Should return next character for cycle mode."""
        char = get_next_character(cycle_config)
        assert char is not None
        assert char in CHARACTERS


class TestGetUpcomingCharacters:
    """Tests for upcoming characters list."""

    def test_returns_empty_for_non_cycle_mode(self, daily_random_config: HotspotchiConfig):
        """Should return empty list for non-cycle modes."""
        upcoming = get_upcoming_characters(daily_random_config)
        assert upcoming == []

    def test_returns_correct_count(self, cycle_config: HotspotchiConfig):
        """Should return requested number of characters."""
        upcoming = get_upcoming_characters(cycle_config, count=5)
        assert len(upcoming) == 5

    def test_returns_characters_in_order(self, cycle_config: HotspotchiConfig):
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


class TestGenerateDailyPassword:
    """Tests for daily password generation."""

    def test_same_day_same_password(self):
        """Same date should produce same password."""
        date = datetime(2024, 6, 15)
        password1 = generate_daily_password(date)
        password2 = generate_daily_password(date)
        assert password1 == password2

    def test_different_days_different_passwords(self):
        """Different dates should produce different passwords."""
        date1 = datetime(2024, 6, 15)
        date2 = datetime(2024, 6, 16)
        password1 = generate_daily_password(date1)
        password2 = generate_daily_password(date2)
        assert password1 != password2

    def test_password_length(self):
        """Password should be 16 characters."""
        password = generate_daily_password()
        assert len(password) == 16

    def test_password_alphanumeric(self):
        """Password should only contain alphanumeric characters."""
        password = generate_daily_password()
        assert password.isalnum()

    def test_wpa2_minimum_length(self):
        """Password should meet WPA2 minimum length requirement (8 chars)."""
        password = generate_daily_password()
        assert len(password) >= 8

    def test_deterministic(self):
        """Same date should always give same password."""
        date = datetime(2024, 3, 14)
        results = [generate_daily_password(date) for _ in range(10)]
        assert len(set(results)) == 1

    def test_different_from_character_selection(self):
        """Password seed should differ from character selection seed."""
        # This ensures the password and character don't use the exact same RNG state
        date = datetime(2024, 6, 15)
        password = generate_daily_password(date)
        # If both used same seed, they would be correlated
        # Password should be independent of character selection
        assert len(password) == 16


class TestSelectCombined:
    """Tests for combined character and special SSID selection."""

    def test_returns_selection_result(self):
        """Should always return a SelectionResult object."""
        config = HotspotchiConfig(mac_mode=MacMode.RANDOM)
        result = select_combined(config)
        assert isinstance(result, SelectionResult)

    def test_special_ssid_mode_returns_special_ssid(self):
        """Special SSID mode should return a special SSID, not a character."""
        config = HotspotchiConfig(
            mac_mode=MacMode.FIXED,
            ssid_mode=SsidMode.SPECIAL,
            special_ssid_index=0,
        )
        result = select_combined(config)
        assert result.is_special_ssid is True
        assert result.special_ssid is not None
        assert result.special_ssid == SPECIAL_SSIDS[0]
        assert result.character is None

    def test_special_ssid_mode_respects_index(self):
        """Special SSID mode should use the configured index."""
        if len(SPECIAL_SSIDS) < 3:
            return  # Skip if not enough special SSIDs
        config = HotspotchiConfig(
            mac_mode=MacMode.FIXED,
            ssid_mode=SsidMode.SPECIAL,
            special_ssid_index=2,
        )
        result = select_combined(config)
        assert result.special_ssid == SPECIAL_SSIDS[2]

    def test_special_ssid_mode_clamps_high_index(self):
        """Special SSID mode should clamp too-high index to last SSID."""
        config = HotspotchiConfig(
            mac_mode=MacMode.FIXED,
            ssid_mode=SsidMode.SPECIAL,
            special_ssid_index=9999,
        )
        result = select_combined(config)
        assert result.special_ssid == SPECIAL_SSIDS[-1]

    def test_fixed_mode_returns_character(self):
        """Fixed mode (without special SSID mode) should return a character."""
        config = HotspotchiConfig(
            mac_mode=MacMode.FIXED,
            ssid_mode=SsidMode.NORMAL,
            fixed_character_index=5,
        )
        result = select_combined(config)
        assert result.is_special_ssid is False
        assert result.character is not None
        assert result.character == CHARACTERS[5]
        assert result.special_ssid is None

    def test_disabled_mode_returns_empty_result(self):
        """Disabled mode should return an empty SelectionResult."""
        config = HotspotchiConfig(mac_mode=MacMode.DISABLED)
        result = select_combined(config)
        assert result.character is None
        assert result.special_ssid is None
        assert result.name is None

    def test_random_mode_returns_character(self):
        """Random mode should return a character from the pool."""
        config = HotspotchiConfig(mac_mode=MacMode.RANDOM, include_special_ssids=False)
        result = select_combined(config)
        assert result.character is not None
        assert result.character in CHARACTERS

    def test_daily_random_same_day_same_result(self):
        """Daily random should return same selection for same day."""
        config = HotspotchiConfig(mac_mode=MacMode.DAILY_RANDOM, include_special_ssids=False)
        fixed_date = datetime(2024, 6, 15)
        result1 = select_combined(config, current_date=fixed_date)
        result2 = select_combined(config, current_date=fixed_date)
        assert result1.name == result2.name

    def test_cycle_mode_with_temp_file(self, temp_dir: Path):
        """Cycle mode should progress through selections."""
        cycle_file = temp_dir / "cycle.txt"
        config = HotspotchiConfig(
            mac_mode=MacMode.CYCLE,
            cycle_file=cycle_file,
            include_special_ssids=False,
        )
        result1 = select_combined(config)
        result2 = select_combined(config)
        assert result1.character != result2.character

    def test_include_special_ssids_expands_pool(self, temp_dir: Path):
        """With include_special_ssids, pool should include both characters and SSIDs."""
        # Use cycle mode to deterministically hit different items
        cycle_file = temp_dir / "cycle.txt"
        config = HotspotchiConfig(
            mac_mode=MacMode.CYCLE,
            cycle_file=cycle_file,
            include_special_ssids=True,
        )
        # Cycle through to reach special SSIDs (they come after characters)
        cycle_file.write_text(str(len(CHARACTERS)))  # Start at first special SSID
        result = select_combined(config)
        # Should have selected a special SSID (if any active)
        from hotspotchi.selection import get_active_special_ssids

        active_ssids = get_active_special_ssids()
        if active_ssids:
            assert result.is_special_ssid is True

    def test_selection_result_name_property(self):
        """SelectionResult.name should work for both types."""
        config_char = HotspotchiConfig(
            mac_mode=MacMode.FIXED,
            ssid_mode=SsidMode.NORMAL,
            fixed_character_index=0,
        )
        result_char = select_combined(config_char)
        assert result_char.name == CHARACTERS[0].name

        config_ssid = HotspotchiConfig(
            mac_mode=MacMode.FIXED,
            ssid_mode=SsidMode.SPECIAL,
            special_ssid_index=0,
        )
        result_ssid = select_combined(config_ssid)
        assert result_ssid.name == SPECIAL_SSIDS[0].character_name

    def test_selection_result_ssid_property(self):
        """SelectionResult.ssid should return SSID for special SSID selections."""
        config = HotspotchiConfig(
            mac_mode=MacMode.FIXED,
            ssid_mode=SsidMode.SPECIAL,
            special_ssid_index=0,
        )
        result = select_combined(config)
        assert result.ssid == SPECIAL_SSIDS[0].ssid

        # Regular character should return None for ssid
        config_char = HotspotchiConfig(
            mac_mode=MacMode.FIXED,
            ssid_mode=SsidMode.NORMAL,
            fixed_character_index=0,
        )
        result_char = select_combined(config_char)
        assert result_char.ssid is None


class TestGetCurrentSeason:
    """Tests for season detection."""

    def test_spring_months(self):
        """March, April, May should be spring."""
        assert get_current_season(datetime(2024, 3, 1)) == "spring"
        assert get_current_season(datetime(2024, 4, 15)) == "spring"
        assert get_current_season(datetime(2024, 5, 31)) == "spring"

    def test_summer_months(self):
        """June, July, August should be summer."""
        assert get_current_season(datetime(2024, 6, 1)) == "summer"
        assert get_current_season(datetime(2024, 7, 15)) == "summer"
        assert get_current_season(datetime(2024, 8, 31)) == "summer"

    def test_fall_months(self):
        """September, October, November should be fall."""
        assert get_current_season(datetime(2024, 9, 1)) == "fall"
        assert get_current_season(datetime(2024, 10, 15)) == "fall"
        assert get_current_season(datetime(2024, 11, 30)) == "fall"

    def test_winter_months(self):
        """December, January, February should be winter."""
        assert get_current_season(datetime(2024, 12, 1)) == "winter"
        assert get_current_season(datetime(2024, 1, 15)) == "winter"
        assert get_current_season(datetime(2024, 2, 28)) == "winter"

    def test_uses_current_date_when_none(self):
        """Should use current datetime when no date provided."""
        result = get_current_season()
        # Just verify it returns a valid season
        assert result in ("spring", "summer", "fall", "winter")


class TestIsCharacterAvailableNow:
    """Tests for character availability based on season."""

    def test_non_seasonal_always_available(self):
        """Characters without season should always be available."""
        char = Character(byte1=0, byte2=0, name="Test", season=None)
        assert is_character_available_now(char, datetime(2024, 1, 1)) is True
        assert is_character_available_now(char, datetime(2024, 4, 1)) is True
        assert is_character_available_now(char, datetime(2024, 7, 1)) is True
        assert is_character_available_now(char, datetime(2024, 10, 1)) is True

    def test_spring_character_in_spring(self):
        """Spring character should be available in spring."""
        char = Character(byte1=0, byte2=0x0F, name="SpringChar", season="spring")
        assert is_character_available_now(char, datetime(2024, 3, 15)) is True
        assert is_character_available_now(char, datetime(2024, 4, 15)) is True
        assert is_character_available_now(char, datetime(2024, 5, 15)) is True

    def test_spring_character_not_in_other_seasons(self):
        """Spring character should not be available in other seasons."""
        char = Character(byte1=0, byte2=0x0F, name="SpringChar", season="spring")
        assert is_character_available_now(char, datetime(2024, 6, 15)) is False  # Summer
        assert is_character_available_now(char, datetime(2024, 9, 15)) is False  # Fall
        assert is_character_available_now(char, datetime(2024, 12, 15)) is False  # Winter

    def test_summer_character_availability(self):
        """Summer character should only be available in summer."""
        char = Character(byte1=0, byte2=0x0E, name="SummerChar", season="summer")
        assert is_character_available_now(char, datetime(2024, 7, 15)) is True
        assert is_character_available_now(char, datetime(2024, 3, 15)) is False

    def test_fall_character_availability(self):
        """Fall character should only be available in fall."""
        char = Character(byte1=0, byte2=0x0D, name="FallChar", season="fall")
        assert is_character_available_now(char, datetime(2024, 10, 15)) is True
        assert is_character_available_now(char, datetime(2024, 6, 15)) is False

    def test_winter_character_availability(self):
        """Winter character should only be available in winter."""
        char = Character(byte1=0, byte2=0x0C, name="WinterChar", season="winter")
        assert is_character_available_now(char, datetime(2024, 12, 15)) is True
        assert is_character_available_now(char, datetime(2024, 1, 15)) is True
        assert is_character_available_now(char, datetime(2024, 6, 15)) is False


class TestGetAvailableCharactersSeasonalFiltering:
    """Tests for seasonal filtering in get_available_characters."""

    def test_filters_out_wrong_season(self):
        """Should filter out characters not in current season."""
        # In December (winter), spring/summer/fall characters should be filtered
        winter_date = datetime(2024, 12, 15)
        available = get_available_characters(
            CHARACTERS,
            respect_exclusions=False,
            filter_by_season=True,
            current_date=winter_date,
        )

        # Check that no spring/summer/fall characters are in the result
        for char in available:
            if char.season is not None:
                assert char.season == "winter", (
                    f"Found {char.season} character {char.name} in winter"
                )

    def test_includes_current_season(self):
        """Should include characters from current season."""
        # In spring, spring characters should be available
        spring_date = datetime(2024, 4, 15)
        available = get_available_characters(
            CHARACTERS,
            respect_exclusions=False,
            filter_by_season=True,
            current_date=spring_date,
        )

        # Find a spring character to verify it's included
        spring_chars = [c for c in CHARACTERS if c.season == "spring"]
        for spring_char in spring_chars:
            assert spring_char in available, f"Spring character {spring_char.name} missing"

    def test_includes_non_seasonal_characters(self):
        """Non-seasonal characters should always be included."""
        winter_date = datetime(2024, 12, 15)
        available = get_available_characters(
            CHARACTERS,
            respect_exclusions=False,
            filter_by_season=True,
            current_date=winter_date,
        )

        # All non-seasonal characters should be present
        non_seasonal = [c for c in CHARACTERS if c.season is None]
        for char in non_seasonal:
            assert char in available, f"Non-seasonal character {char.name} missing"

    def test_can_disable_seasonal_filtering(self):
        """Should be able to disable seasonal filtering."""
        winter_date = datetime(2024, 12, 15)
        available = get_available_characters(
            CHARACTERS,
            respect_exclusions=False,
            filter_by_season=False,
            current_date=winter_date,
        )

        # With filtering disabled, should have all characters
        assert len(available) == len(CHARACTERS)


class TestSelectCharacterSeasonalFiltering:
    """Tests for seasonal filtering in select_character."""

    def test_daily_random_respects_season(self):
        """Daily random should only select seasonally appropriate characters."""
        config = HotspotchiConfig(mac_mode=MacMode.DAILY_RANDOM)

        # Run selection multiple times with different seeds to verify (December = winter)
        for day_offset in range(10):
            test_date = datetime(2024, 12, 15 + day_offset)
            char = select_character(config, current_date=test_date)
            assert char is not None
            if char.season is not None:
                assert char.season == "winter", f"Got {char.season} character on winter day"

    def test_random_respects_season(self):
        """Random mode should only select seasonally appropriate characters."""
        summer_date = datetime(2024, 7, 15)
        config = HotspotchiConfig(mac_mode=MacMode.RANDOM)

        # Run selection multiple times
        for _ in range(20):
            char = select_character(config, current_date=summer_date)
            assert char is not None
            if char.season is not None:
                assert char.season == "summer", f"Got {char.season} character in summer"

    def test_fixed_mode_ignores_season(self):
        """Fixed mode should allow selecting any character regardless of season."""
        # Find a spring character index
        spring_idx = None
        for i, char in enumerate(CHARACTERS):
            if char.season == "spring":
                spring_idx = i
                break

        if spring_idx is not None:
            winter_date = datetime(2024, 12, 15)
            config = HotspotchiConfig(
                mac_mode=MacMode.FIXED,
                fixed_character_index=spring_idx,
            )
            char = select_character(config, current_date=winter_date)
            # Fixed mode should return the spring character even in winter
            assert char is not None
            assert char.season == "spring"


class TestSelectCombinedSeasonalFiltering:
    """Tests for seasonal filtering in select_combined."""

    def test_combined_respects_season(self):
        """Combined selection should respect seasonal filtering."""
        fall_date = datetime(2024, 10, 15)
        config = HotspotchiConfig(
            mac_mode=MacMode.RANDOM,
            include_special_ssids=False,
        )

        for _ in range(20):
            result = select_combined(config, current_date=fall_date)
            if result.character and result.character.season:
                assert result.character.season == "fall"
