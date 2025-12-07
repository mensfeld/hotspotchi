"""Tests for web API routes."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from hotspotchi.characters import CHARACTERS, SPECIAL_SSIDS
from hotspotchi.exclusions import get_exclusion_manager, reset_exclusion_manager
from hotspotchi.web.app import app


@pytest.fixture
def client():
    """Create a test client with a fresh app instance."""
    # Reset the exclusion manager state before each test
    exclusion_manager = get_exclusion_manager()
    exclusion_manager.clear_all()

    with TestClient(app) as c:
        yield c


class TestSSIDExclusionEndpoints:
    """Tests for SSID exclusion API endpoints."""

    def test_list_ssids_includes_excluded_field(self, client: TestClient):
        """GET /api/ssids should include excluded field for each SSID."""
        response = client.get("/api/ssids")
        assert response.status_code == 200
        ssids = response.json()
        assert len(ssids) > 0
        # Each SSID should have an 'excluded' field
        for ssid in ssids:
            assert "excluded" in ssid
            assert isinstance(ssid["excluded"], bool)

    def test_list_ssids_available_only_filter(self, client: TestClient):
        """GET /api/ssids?available_only=true should exclude excluded SSIDs."""
        # First exclude an SSID
        exclude_response = client.post("/api/ssids/0/exclude")
        assert exclude_response.status_code == 200

        # Now get available only
        response = client.get("/api/ssids?available_only=true")
        assert response.status_code == 200
        ssids = response.json()

        # Index 0 should not be in the list
        indices = [s["index"] for s in ssids]
        assert 0 not in indices

    def test_list_ssids_excluded_only_filter(self, client: TestClient):
        """GET /api/ssids?excluded_only=true should return only excluded SSIDs."""
        # First exclude an SSID
        exclude_response = client.post("/api/ssids/0/exclude")
        assert exclude_response.status_code == 200

        # Now get excluded only
        response = client.get("/api/ssids?excluded_only=true")
        assert response.status_code == 200
        ssids = response.json()

        # Only index 0 should be in the list
        assert len(ssids) == 1
        assert ssids[0]["index"] == 0
        assert ssids[0]["excluded"] is True

    def test_get_ssid_includes_excluded_field(self, client: TestClient):
        """GET /api/ssids/{index} should include excluded field."""
        response = client.get("/api/ssids/0")
        assert response.status_code == 200
        ssid = response.json()
        assert "excluded" in ssid
        assert ssid["excluded"] is False

    def test_exclude_ssid(self, client: TestClient):
        """POST /api/ssids/{index}/exclude should exclude the SSID."""
        response = client.post("/api/ssids/0/exclude")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "excluded"
        assert data["index"] == 0
        assert data["character"] == SPECIAL_SSIDS[0].character_name

        # Verify it's now excluded
        get_response = client.get("/api/ssids/0")
        assert get_response.json()["excluded"] is True

    def test_exclude_ssid_not_found(self, client: TestClient):
        """POST /api/ssids/{index}/exclude should return 404 for invalid index."""
        response = client.post("/api/ssids/9999/exclude")
        assert response.status_code == 404

    def test_include_ssid(self, client: TestClient):
        """POST /api/ssids/{index}/include should include a previously excluded SSID."""
        # First exclude
        client.post("/api/ssids/0/exclude")

        # Then include
        response = client.post("/api/ssids/0/include")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "included"
        assert data["index"] == 0

        # Verify it's now included
        get_response = client.get("/api/ssids/0")
        assert get_response.json()["excluded"] is False

    def test_include_ssid_not_found(self, client: TestClient):
        """POST /api/ssids/{index}/include should return 404 for invalid index."""
        response = client.post("/api/ssids/9999/include")
        assert response.status_code == 404

    def test_toggle_ssid_exclusion_excludes(self, client: TestClient):
        """POST /api/ssids/{index}/toggle-exclusion should toggle to excluded."""
        response = client.post("/api/ssids/0/toggle-exclusion")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "excluded"
        assert data["excluded"] is True

    def test_toggle_ssid_exclusion_includes(self, client: TestClient):
        """POST /api/ssids/{index}/toggle-exclusion should toggle to included."""
        # First exclude
        client.post("/api/ssids/0/exclude")

        # Then toggle (should include)
        response = client.post("/api/ssids/0/toggle-exclusion")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "included"
        assert data["excluded"] is False

    def test_toggle_ssid_exclusion_not_found(self, client: TestClient):
        """POST /api/ssids/{index}/toggle-exclusion should return 404 for invalid index."""
        response = client.post("/api/ssids/9999/toggle-exclusion")
        assert response.status_code == 404

    def test_get_ssid_exclusions(self, client: TestClient):
        """GET /api/ssid-exclusions should return exclusion summary."""
        # Exclude a couple of SSIDs
        client.post("/api/ssids/0/exclude")
        client.post("/api/ssids/1/exclude")

        response = client.get("/api/ssid-exclusions")
        assert response.status_code == 200
        data = response.json()
        assert data["excluded_count"] == 2
        assert 0 in data["excluded_indices"]
        assert 1 in data["excluded_indices"]
        assert data["total_ssids"] == len(SPECIAL_SSIDS)

    def test_clear_ssid_exclusions(self, client: TestClient):
        """DELETE /api/ssid-exclusions should clear all SSID exclusions."""
        # Exclude some SSIDs
        client.post("/api/ssids/0/exclude")
        client.post("/api/ssids/1/exclude")

        # Clear all
        response = client.delete("/api/ssid-exclusions")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # Verify none are excluded
        exclusions = client.get("/api/ssid-exclusions").json()
        assert exclusions["excluded_count"] == 0

    def test_clear_all_exclusions(self, client: TestClient):
        """DELETE /api/all-exclusions should clear both character and SSID exclusions."""
        # Exclude a character and an SSID
        client.post("/api/characters/0/exclude")
        client.post("/api/ssids/0/exclude")

        # Clear all
        response = client.delete("/api/all-exclusions")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # Verify none are excluded
        ssid_exclusions = client.get("/api/ssid-exclusions").json()
        assert ssid_exclusions["excluded_count"] == 0

        char_exclusions = client.get("/api/exclusions").json()
        assert char_exclusions["excluded_count"] == 0


class TestStatusEndpoint:
    """Tests for the status API endpoint."""

    def test_get_status(self, client: TestClient):
        """GET /api/status should return current status."""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "ssid" in data
        assert "mac_mode" in data
        assert "ssid_mode" in data
        assert "total_characters" in data
        assert "available_characters" in data
        assert "excluded_characters" in data
        assert "total_special_ssids" in data

    def test_status_shows_character_counts(self, client: TestClient):
        """Status should show correct character counts."""
        response = client.get("/api/status")
        data = response.json()
        assert data["total_characters"] == len(CHARACTERS)
        assert data["available_characters"] == len(CHARACTERS)
        assert data["excluded_characters"] == 0


class TestCharacterEndpoints:
    """Tests for character API endpoints."""

    def test_list_characters(self, client: TestClient):
        """GET /api/characters should return all characters."""
        response = client.get("/api/characters")
        assert response.status_code == 200
        chars = response.json()
        assert len(chars) == len(CHARACTERS)

    def test_list_characters_with_search(self, client: TestClient):
        """GET /api/characters?search=mametchi should filter by name."""
        response = client.get("/api/characters?search=mametchi")
        assert response.status_code == 200
        chars = response.json()
        assert len(chars) > 0
        for char in chars:
            assert "mametchi" in char["name"].lower()

    def test_list_characters_excluded_only(self, client: TestClient):
        """GET /api/characters?excluded_only=true should return only excluded."""
        # First exclude a character
        client.post("/api/characters/0/exclude")

        response = client.get("/api/characters?excluded_only=true")
        assert response.status_code == 200
        chars = response.json()
        assert len(chars) == 1
        assert chars[0]["index"] == 0
        assert chars[0]["excluded"] is True

    def test_list_characters_available_only(self, client: TestClient):
        """GET /api/characters?available_only=true should exclude excluded chars."""
        # First exclude a character
        client.post("/api/characters/0/exclude")

        response = client.get("/api/characters?available_only=true")
        assert response.status_code == 200
        chars = response.json()
        indices = [c["index"] for c in chars]
        assert 0 not in indices

    def test_get_character(self, client: TestClient):
        """GET /api/characters/{index} should return specific character."""
        response = client.get("/api/characters/0")
        assert response.status_code == 200
        char = response.json()
        assert char["index"] == 0
        assert char["name"] == CHARACTERS[0].name
        assert "mac_address" in char
        assert "excluded" in char

    def test_get_character_not_found(self, client: TestClient):
        """GET /api/characters/{index} should return 404 for invalid index."""
        response = client.get("/api/characters/9999")
        assert response.status_code == 404

    def test_exclude_character(self, client: TestClient):
        """POST /api/characters/{index}/exclude should exclude character."""
        response = client.post("/api/characters/0/exclude")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "excluded"

    def test_exclude_character_not_found(self, client: TestClient):
        """POST /api/characters/{index}/exclude should return 404 for invalid."""
        response = client.post("/api/characters/9999/exclude")
        assert response.status_code == 404

    def test_include_character(self, client: TestClient):
        """POST /api/characters/{index}/include should include character."""
        client.post("/api/characters/0/exclude")
        response = client.post("/api/characters/0/include")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "included"

    def test_toggle_character_exclusion(self, client: TestClient):
        """POST /api/characters/{index}/toggle-exclusion should toggle."""
        # First toggle (exclude)
        response = client.post("/api/characters/0/toggle-exclusion")
        assert response.status_code == 200
        assert response.json()["excluded"] is True

        # Second toggle (include)
        response = client.post("/api/characters/0/toggle-exclusion")
        assert response.status_code == 200
        assert response.json()["excluded"] is False


class TestConfigEndpoint:
    """Tests for the config API endpoint."""

    def test_update_config_mac_mode(self, client: TestClient):
        """POST /api/config should update mac_mode."""
        response = client.post("/api/config", json={"mac_mode": "random"})
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_update_config_invalid_mac_mode(self, client: TestClient):
        """POST /api/config should reject invalid mac_mode."""
        response = client.post("/api/config", json={"mac_mode": "invalid"})
        assert response.status_code == 400

    def test_update_config_ssid_mode(self, client: TestClient):
        """POST /api/config should update ssid_mode."""
        response = client.post("/api/config", json={"ssid_mode": "special"})
        assert response.status_code == 200

    def test_update_config_invalid_ssid_mode(self, client: TestClient):
        """POST /api/config should reject invalid ssid_mode."""
        response = client.post("/api/config", json={"ssid_mode": "invalid"})
        assert response.status_code == 400

    def test_update_config_rotation_mode_resets_ssid_mode(self, client: TestClient):
        """Switching to rotation mode should reset ssid_mode to normal."""
        # First set ssid_mode to special
        client.post("/api/config", json={"ssid_mode": "special"})

        # Now switch to daily_random
        client.post("/api/config", json={"mac_mode": "daily_random"})

        # Check status - ssid_mode should be normal
        status = client.get("/api/status").json()
        assert status["ssid_mode"] == "normal"

    def test_update_config_special_ssid_index(self, client: TestClient):
        """POST /api/config should update special_ssid_index."""
        response = client.post("/api/config", json={"special_ssid_index": 5})
        assert response.status_code == 200

    def test_update_config_invalid_special_ssid_index(self, client: TestClient):
        """POST /api/config should reject invalid special_ssid_index."""
        response = client.post("/api/config", json={"special_ssid_index": 9999})
        assert response.status_code == 400

    def test_update_config_fixed_character_index(self, client: TestClient):
        """POST /api/config should update fixed_character_index."""
        response = client.post("/api/config", json={"fixed_character_index": 5})
        assert response.status_code == 200

    def test_update_config_invalid_fixed_character_index(self, client: TestClient):
        """POST /api/config should reject invalid fixed_character_index."""
        response = client.post("/api/config", json={"fixed_character_index": 9999})
        assert response.status_code == 400


class TestSetCharacterEndpoint:
    """Tests for the set character endpoint."""

    def test_set_character(self, client: TestClient):
        """POST /api/character/{index} should set the character."""
        response = client.post("/api/character/5")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "character" in data
        assert "mac_address" in data

    def test_set_character_invalid_index(self, client: TestClient):
        """POST /api/character/{index} should return 400 for invalid index."""
        response = client.post("/api/character/9999")
        assert response.status_code == 400


class TestSetSpecialSSIDEndpoint:
    """Tests for the set special SSID endpoint."""

    def test_set_special_ssid(self, client: TestClient):
        """POST /api/ssid/{index} should set the special SSID."""
        response = client.post("/api/ssid/5")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "ssid" in data
        assert "character" in data

    def test_set_special_ssid_invalid_index(self, client: TestClient):
        """POST /api/ssid/{index} should return 400 for invalid index."""
        response = client.post("/api/ssid/9999")
        assert response.status_code == 400


class TestExclusionsEndpoint:
    """Tests for the exclusions endpoint."""

    def test_get_exclusions(self, client: TestClient):
        """GET /api/exclusions should return exclusion summary."""
        client.post("/api/characters/0/exclude")
        client.post("/api/characters/1/exclude")

        response = client.get("/api/exclusions")
        assert response.status_code == 200
        data = response.json()
        assert data["excluded_count"] == 2
        assert 0 in data["excluded_indices"]
        assert 1 in data["excluded_indices"]

    def test_clear_exclusions(self, client: TestClient):
        """DELETE /api/exclusions should clear all character exclusions."""
        client.post("/api/characters/0/exclude")
        client.post("/api/characters/1/exclude")

        response = client.delete("/api/exclusions")
        assert response.status_code == 200

        exclusions = client.get("/api/exclusions").json()
        assert exclusions["excluded_count"] == 0


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client: TestClient):
        """GET / should return health status."""
        response = client.get("/")
        # May redirect to dashboard, so accept 200 or 307
        assert response.status_code in (200, 307)
