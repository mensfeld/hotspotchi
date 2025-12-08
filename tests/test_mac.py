"""Tests for MAC address utilities."""

import pytest

from hotspotchi.characters import CHARACTERS, Character
from hotspotchi.mac import (
    MAC_PREFIX,
    create_mac_address,
    format_mac,
    is_hotspotchi_mac,
    is_valid_mac,
    parse_mac_bytes,
)


class TestCreateMacAddress:
    """Tests for MAC address creation."""

    def test_correct_format(self):
        """MAC should be in xx:xx:xx:xx:xx:xx format."""
        char = Character(0x00, 0x00, "Mametchi")
        mac = create_mac_address(char)
        assert len(mac.split(":")) == 6

    def test_locally_administered_prefix(self):
        """MAC should start with 02 (locally administered)."""
        char = Character(0x00, 0x00, "Mametchi")
        mac = create_mac_address(char)
        assert mac.startswith("02:")

    def test_tama_signature(self):
        """MAC should contain TAMA signature bytes."""
        char = Character(0x00, 0x00, "Mametchi")
        mac = create_mac_address(char)
        assert "7a:6d:a0" in mac.lower()

    def test_character_bytes_at_end(self):
        """Character bytes should be last two octets."""
        char = Character(0x01, 0xA0, "Watawatatchi")
        mac = create_mac_address(char)
        assert mac.endswith(":01:a0")

    def test_full_mac_format(self):
        """Test complete MAC address format."""
        char = Character(0x02, 0xF0, "Sunopotchi")
        mac = create_mac_address(char)
        assert mac == "02:7a:6d:a0:02:f0"

    def test_hex_formatting(self):
        """Hex values should be zero-padded."""
        char = Character(0x00, 0x05, "Test")
        mac = create_mac_address(char)
        assert ":00:05" in mac

    def test_all_characters_produce_valid_mac(self):
        """All characters should produce valid MAC addresses."""
        for char in CHARACTERS:
            mac = create_mac_address(char)
            assert is_valid_mac(mac), f"Invalid MAC for {char.name}"


class TestFormatMac:
    """Tests for MAC address formatting."""

    def test_uppercase(self):
        """Should convert to uppercase."""
        assert format_mac("02:7a:6d:a0:00:00") == "02:7A:6D:A0:00:00"

    def test_lowercase(self):
        """Should convert to lowercase when requested."""
        assert format_mac("02:7A:6D:A0:00:00", uppercase=False) == "02:7a:6d:a0:00:00"

    def test_preserves_format(self):
        """Should preserve colon format."""
        mac = "02:7a:6d:a0:12:34"
        assert format_mac(mac).count(":") == 5

    def test_already_uppercase(self):
        """Should handle already uppercase input."""
        mac = "02:7A:6D:A0:00:00"
        assert format_mac(mac) == mac

    def test_already_lowercase(self):
        """Should handle already lowercase input."""
        mac = "02:7a:6d:a0:00:00"
        assert format_mac(mac, uppercase=False) == mac


class TestParseMacBytes:
    """Tests for extracting bytes from MAC."""

    def test_parse_bytes(self):
        """Should extract character bytes from MAC."""
        byte1, byte2 = parse_mac_bytes("02:7A:6D:A0:01:B0")
        assert byte1 == 0x01
        assert byte2 == 0xB0

    def test_parse_lowercase(self):
        """Should handle lowercase input."""
        byte1, byte2 = parse_mac_bytes("02:7a:6d:a0:ff:ee")
        assert byte1 == 0xFF
        assert byte2 == 0xEE

    def test_parse_zero_bytes(self):
        """Should handle zero bytes."""
        byte1, byte2 = parse_mac_bytes("02:7A:6D:A0:00:00")
        assert byte1 == 0
        assert byte2 == 0

    def test_invalid_format_too_short(self):
        """Should raise for invalid format."""
        with pytest.raises(ValueError):
            parse_mac_bytes("02:7A:6D")

    def test_invalid_format_too_long(self):
        """Should raise for too many parts."""
        with pytest.raises(ValueError):
            parse_mac_bytes("02:7A:6D:A0:01:B0:FF")

    def test_invalid_hex_values(self):
        """Should raise for invalid hex."""
        with pytest.raises(ValueError):
            parse_mac_bytes("02:7A:6D:A0:GG:HH")

    def test_roundtrip(self):
        """Creating and parsing should round-trip."""
        char = Character(0x12, 0x34, "Test")
        mac = create_mac_address(char)
        byte1, byte2 = parse_mac_bytes(mac)
        assert byte1 == 0x12
        assert byte2 == 0x34


class TestIsValidMac:
    """Tests for MAC address validation."""

    def test_valid_mac(self):
        """Should accept valid MAC."""
        assert is_valid_mac("02:7A:6D:A0:00:00")

    def test_valid_lowercase(self):
        """Should accept lowercase MAC."""
        assert is_valid_mac("02:7a:6d:a0:00:00")

    def test_too_short(self):
        """Should reject too-short MAC."""
        assert not is_valid_mac("02:7A:6D:A0:00")

    def test_too_long(self):
        """Should reject too-long MAC."""
        assert not is_valid_mac("02:7A:6D:A0:00:00:00")

    def test_invalid_chars(self):
        """Should reject invalid characters."""
        assert not is_valid_mac("02:7A:6D:A0:GG:00")

    def test_wrong_separator(self):
        """Should reject wrong separator."""
        assert not is_valid_mac("02-7A-6D-A0-00-00")

    def test_missing_separator(self):
        """Should reject missing separators."""
        assert not is_valid_mac("027A6DA00000")

    def test_empty_string(self):
        """Should reject empty string."""
        assert not is_valid_mac("")

    def test_none(self):
        """Should handle None gracefully."""
        assert not is_valid_mac(None)  # type: ignore

    def test_single_digit_parts(self):
        """Should reject single-digit parts."""
        assert not is_valid_mac("2:7A:6D:A0:0:0")


class TestIsHotspotchiMac:
    """Tests for Hotspotchi MAC detection."""

    def test_recognizes_hotspotchi_mac(self):
        """Should recognize Hotspotchi-generated MAC."""
        char = Character(0x00, 0x00, "Test")
        mac = create_mac_address(char)
        assert is_hotspotchi_mac(mac)

    def test_recognizes_uppercase(self):
        """Should recognize uppercase MAC."""
        assert is_hotspotchi_mac("02:7A:6D:A0:12:34")

    def test_recognizes_lowercase(self):
        """Should recognize lowercase MAC."""
        assert is_hotspotchi_mac("02:7a:6d:a0:12:34")

    def test_rejects_different_prefix(self):
        """Should reject non-Hotspotchi MAC."""
        assert not is_hotspotchi_mac("00:11:22:33:44:55")

    def test_mac_prefix_constant(self):
        """MAC_PREFIX should be correct."""
        assert MAC_PREFIX == "02:7a:6d:a0"
