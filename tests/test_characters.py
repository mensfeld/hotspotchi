"""Tests for character data integrity."""

import pytest

from hotspotchi.characters import (
    CHARACTERS,
    SPECIAL_SSIDS,
    Character,
    SpecialSSID,
    get_active_special_ssids,
    get_character_by_bytes,
    get_character_by_name,
    get_seasonal_characters,
)


class TestCharacterData:
    """Validate character data integrity."""

    def test_all_characters_have_valid_bytes(self):
        """All characters should have bytes in 0-255 range."""
        for char in CHARACTERS:
            assert 0 <= char.byte1 <= 255, f"Invalid byte1 for {char.name}"
            assert 0 <= char.byte2 <= 255, f"Invalid byte2 for {char.name}"

    def test_all_characters_have_names(self):
        """All characters should have non-empty names."""
        for char in CHARACTERS:
            assert char.name, f"Empty name for character with bytes {char.byte1}, {char.byte2}"
            assert len(char.name) > 0

    def test_no_duplicate_byte_pairs(self):
        """No two characters should share the same byte pair."""
        seen = set()
        for char in CHARACTERS:
            pair = (char.byte1, char.byte2)
            assert pair not in seen, f"Duplicate bytes {pair} for {char.name}"
            seen.add(pair)

    def test_expected_character_count(self):
        """Should have at least 68 characters (53 common + 16 seasonal)."""
        assert len(CHARACTERS) >= 68

    def test_seasonal_characters_have_valid_seasons(self):
        """Seasonal characters should have valid season values."""
        valid_seasons = {"spring", "summer", "fall", "winter", None}
        for char in CHARACTERS:
            assert char.season in valid_seasons, f"Invalid season {char.season} for {char.name}"

    def test_character_immutability(self):
        """Characters should be immutable (frozen dataclass)."""
        char = CHARACTERS[0]
        with pytest.raises(AttributeError):
            char.name = "Modified"


class TestSpecialSSIDData:
    """Validate special SSID data integrity."""

    def test_all_ssids_have_names(self):
        """All special SSIDs should have character names."""
        for ssid in SPECIAL_SSIDS:
            assert ssid.character_name, f"Empty character_name for SSID {ssid.ssid[:20]}..."

    def test_ssid_length(self):
        """All SSIDs should be non-empty and at most 32 characters."""
        for ssid in SPECIAL_SSIDS:
            assert len(ssid.ssid) > 0, f"Empty SSID for {ssid.character_name}"
            assert len(ssid.ssid) <= 32, f"SSID too long for {ssid.character_name}"

    def test_no_duplicate_ssids(self):
        """No duplicate SSIDs."""
        ssids = [s.ssid for s in SPECIAL_SSIDS]
        assert len(ssids) == len(set(ssids)), "Duplicate SSIDs found"

    def test_expected_ssid_count(self):
        """Should have at least 20 special SSIDs."""
        assert len(SPECIAL_SSIDS) >= 20

    def test_all_ssids_have_notes(self):
        """All SSIDs should have notes."""
        for ssid in SPECIAL_SSIDS:
            assert ssid.notes, f"Empty notes for {ssid.character_name}"


class TestCharacterLookup:
    """Test character lookup functions."""

    def test_get_character_by_name_exists(self):
        """Should find existing character by name."""
        char = get_character_by_name("Mametchi")
        assert char is not None
        assert char.name == "Mametchi"

    def test_get_character_by_name_case_insensitive(self):
        """Should find character regardless of case."""
        char = get_character_by_name("mametchi")
        assert char is not None
        assert char.name == "Mametchi"

    def test_get_character_by_name_not_found(self):
        """Should return None for unknown character."""
        char = get_character_by_name("NonexistentCharacter")
        assert char is None

    def test_get_character_by_bytes_exists(self):
        """Should find character by byte values."""
        char = get_character_by_bytes(0x00, 0x00)
        assert char is not None
        assert char.name == "Mametchi"

    def test_get_character_by_bytes_not_found(self):
        """Should return None for unknown bytes."""
        char = get_character_by_bytes(0xFF, 0xFF)
        assert char is None

    def test_get_seasonal_characters_spring(self):
        """Should return spring characters."""
        chars = get_seasonal_characters("spring")
        assert len(chars) == 4
        assert all(c.season == "spring" for c in chars)

    def test_get_seasonal_characters_all_seasons(self):
        """Should return characters for all seasons."""
        for season in ["spring", "summer", "fall", "winter"]:
            chars = get_seasonal_characters(season)
            assert len(chars) == 4, f"Expected 4 {season} characters"

    def test_get_active_special_ssids(self):
        """Should filter out inactive SSIDs."""
        active = get_active_special_ssids()
        assert all(s.active for s in active)
        # Should be fewer than total if any are inactive
        inactive_count = sum(1 for s in SPECIAL_SSIDS if not s.active)
        assert len(active) == len(SPECIAL_SSIDS) - inactive_count


class TestCharacterDataclass:
    """Test Character dataclass behavior."""

    def test_create_valid_character(self):
        """Should create character with valid bytes."""
        char = Character(0x00, 0x00, "Test")
        assert char.byte1 == 0
        assert char.byte2 == 0
        assert char.name == "Test"
        assert char.season is None

    def test_create_character_with_season(self):
        """Should create character with season."""
        char = Character(0x00, 0x0F, "Spring Test", season="spring")
        assert char.season == "spring"

    def test_character_invalid_byte1(self):
        """Should reject invalid byte1 value."""
        with pytest.raises(ValueError):
            Character(256, 0, "Invalid")

    def test_character_invalid_byte2(self):
        """Should reject invalid byte2 value."""
        with pytest.raises(ValueError):
            Character(0, -1, "Invalid")

    def test_character_equality(self):
        """Characters with same values should be equal."""
        char1 = Character(0x01, 0x02, "Test")
        char2 = Character(0x01, 0x02, "Test")
        assert char1 == char2

    def test_character_hashable(self):
        """Characters should be hashable (usable in sets/dicts)."""
        char = Character(0x01, 0x02, "Test")
        char_set = {char}
        assert char in char_set


class TestSpecialSSIDDataclass:
    """Test SpecialSSID dataclass behavior."""

    def test_create_valid_ssid(self):
        """Should create valid special SSID."""
        ssid = SpecialSSID(
            ssid="TestSSID123",
            character_name="Test Character",
            notes="Test notes",
        )
        assert ssid.ssid == "TestSSID123"
        assert ssid.character_name == "Test Character"
        assert ssid.active is True  # Default

    def test_create_inactive_ssid(self):
        """Should create inactive special SSID."""
        ssid = SpecialSSID(
            ssid="TestSSID123",
            character_name="Test Character",
            notes="Test notes",
            active=False,
        )
        assert ssid.active is False
