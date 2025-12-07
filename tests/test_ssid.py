"""Tests for SSID resolution logic."""

from hotspotchi.characters import SPECIAL_SSIDS
from hotspotchi.config import HotSpotchiConfig, SsidMode
from hotspotchi.ssid import (
    find_ssid_by_character,
    find_ssid_by_ssid_string,
    get_ssid_index,
    get_ssid_index_by_character,
    is_valid_ssid,
    list_special_ssids,
    resolve_ssid,
)


class TestResolveSsid:
    """Tests for SSID resolution."""

    def test_normal_mode_default_ssid(self, default_config: HotSpotchiConfig):
        """Normal mode should return default SSID."""
        ssid, char = resolve_ssid(default_config)
        assert ssid == "HotSpotchi"
        assert char is None

    def test_custom_mode(self, custom_ssid_config: HotSpotchiConfig):
        """Custom mode should return custom SSID."""
        ssid, char = resolve_ssid(custom_ssid_config)
        assert ssid == "MyCustomNetwork"
        assert char is None

    def test_special_mode(self, special_ssid_config: HotSpotchiConfig):
        """Special mode should return special SSID and character."""
        ssid, char = resolve_ssid(special_ssid_config)
        # First special SSID is Angel & Devil
        assert ssid == SPECIAL_SSIDS[0].ssid
        assert char == SPECIAL_SSIDS[0].character_name

    def test_special_mode_index_bounds(self):
        """Special mode should clamp to valid index."""
        config = HotSpotchiConfig(
            ssid_mode=SsidMode.SPECIAL,
            special_ssid_index=9999,
        )
        ssid, char = resolve_ssid(config)
        # Should get last SSID, not crash
        assert ssid == SPECIAL_SSIDS[-1].ssid
        assert char is not None

    def test_custom_mode_without_ssid(self):
        """Custom mode without SSID should fall back to default."""
        config = HotSpotchiConfig(
            ssid_mode=SsidMode.CUSTOM,
            custom_ssid=None,
        )
        ssid, char = resolve_ssid(config)
        assert ssid == config.default_ssid


class TestFindSsidByCharacter:
    """Tests for character-to-SSID lookup."""

    def test_find_existing_character(self):
        """Should find SSID for existing character."""
        result = find_ssid_by_character("Angel & Devil")
        assert result is not None
        assert result.character_name == "Angel & Devil"

    def test_case_insensitive(self):
        """Search should be case insensitive."""
        result = find_ssid_by_character("angel & devil")
        assert result is not None

    def test_not_found_returns_none(self):
        """Should return None for unknown character."""
        result = find_ssid_by_character("NonexistentCharacter")
        assert result is None


class TestFindSsidBySsidString:
    """Tests for SSID string lookup."""

    def test_find_existing_ssid(self):
        """Should find by SSID string."""
        first_ssid = SPECIAL_SSIDS[0].ssid
        result = find_ssid_by_ssid_string(first_ssid)
        assert result is not None
        assert result.ssid == first_ssid

    def test_not_found_returns_none(self):
        """Should return None for unknown SSID."""
        result = find_ssid_by_ssid_string("NotARealSSID")
        assert result is None


class TestGetSsidIndex:
    """Tests for SSID index lookup."""

    def test_find_existing_ssid_index(self):
        """Should find index for existing SSID."""
        first_ssid = SPECIAL_SSIDS[0].ssid
        index = get_ssid_index(first_ssid)
        assert index == 0

    def test_not_found_returns_none(self):
        """Should return None for unknown SSID."""
        index = get_ssid_index("NotARealSSID")
        assert index is None

    def test_all_ssids_have_index(self):
        """All SSIDs should be findable by index."""
        for i, ssid in enumerate(SPECIAL_SSIDS):
            assert get_ssid_index(ssid.ssid) == i


class TestGetSsidIndexByCharacter:
    """Tests for character-to-index lookup."""

    def test_find_by_character_name(self):
        """Should find index by character name."""
        first_char = SPECIAL_SSIDS[0].character_name
        index = get_ssid_index_by_character(first_char)
        assert index == 0

    def test_case_insensitive(self):
        """Should be case insensitive."""
        first_char = SPECIAL_SSIDS[0].character_name.lower()
        index = get_ssid_index_by_character(first_char)
        assert index == 0

    def test_not_found_returns_none(self):
        """Should return None for unknown character."""
        index = get_ssid_index_by_character("NonexistentCharacter")
        assert index is None


class TestIsValidSsid:
    """Tests for SSID validation."""

    def test_valid_ssid(self):
        """Should accept valid SSID."""
        assert is_valid_ssid("MyNetwork")

    def test_valid_with_spaces(self):
        """Should accept SSID with spaces."""
        assert is_valid_ssid("My Network Name")

    def test_valid_with_numbers(self):
        """Should accept SSID with numbers."""
        assert is_valid_ssid("Network123")

    def test_valid_with_special_chars(self):
        """Should accept SSID with special characters."""
        assert is_valid_ssid("My-Network_2.4GHz")

    def test_max_length(self):
        """Should accept 32 character SSID."""
        assert is_valid_ssid("a" * 32)

    def test_too_long(self):
        """Should reject SSID over 32 characters."""
        assert not is_valid_ssid("a" * 33)

    def test_empty_string(self):
        """Should reject empty SSID."""
        assert not is_valid_ssid("")

    def test_non_printable(self):
        """Should reject non-printable characters."""
        assert not is_valid_ssid("Network\x00")

    def test_all_special_ssids_valid(self):
        """All special SSIDs should pass validation."""
        for ssid in SPECIAL_SSIDS:
            assert is_valid_ssid(ssid.ssid), f"Invalid SSID: {ssid.ssid}"


class TestListSpecialSsids:
    """Tests for listing special SSIDs."""

    def test_returns_all_with_indices(self):
        """Should return all SSIDs with their indices."""
        result = list_special_ssids(active_only=False)
        assert len(result) == len(SPECIAL_SSIDS)
        # Check indices are correct
        for i, (index, ssid) in enumerate(result):
            assert index == i
            assert ssid == SPECIAL_SSIDS[i]

    def test_active_only_filters(self):
        """Should filter inactive SSIDs when requested."""
        all_ssids = list_special_ssids(active_only=False)
        active_ssids = list_special_ssids(active_only=True)

        inactive_count = sum(1 for _, s in all_ssids if not s.active)
        assert len(active_ssids) == len(all_ssids) - inactive_count

    def test_active_only_all_active(self):
        """Active-only list should only contain active SSIDs."""
        active_ssids = list_special_ssids(active_only=True)
        for _, ssid in active_ssids:
            assert ssid.active
