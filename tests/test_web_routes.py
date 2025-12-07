"""Tests for web API routes."""

import pytest
from fastapi.testclient import TestClient

from hotspotchi.characters import CHARACTERS, SPECIAL_SSIDS
from hotspotchi.exclusions import get_exclusion_manager
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


class TestDebugEndpoint:
    """Tests for the debug API endpoint."""

    def test_get_debug_info(self, client: TestClient):
        """GET /api/debug should return debug information."""
        response = client.get("/api/debug")
        assert response.status_code == 200
        data = response.json()

        # Check structure - debug info has these top-level keys
        assert "config" in data or "timestamp" in data

    def test_debug_config_section(self, client: TestClient):
        """Debug info should include config details."""
        response = client.get("/api/debug")
        data = response.json()

        # The debug response should have config info
        assert "config" in data
        config = data["config"]
        assert isinstance(config, dict)


class TestHealthEndpointExtended:
    """Additional tests for health-related endpoints."""

    def test_health_check_endpoint(self, client: TestClient):
        """GET /health should return health status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestDashboardEndpoint:
    """Tests for the dashboard endpoint."""

    def test_dashboard_renders(self, client: TestClient):
        """GET / should render the dashboard page."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestUpcomingEndpoint:
    """Tests for the upcoming characters endpoint."""

    def test_upcoming_not_cycle_mode(self, client: TestClient):
        """GET /api/upcoming should return empty when not in cycle mode."""
        # Default mode is daily_random, not cycle
        response = client.get("/api/upcoming")
        assert response.status_code == 200
        assert response.json() == []

    def test_upcoming_with_count(self, client: TestClient):
        """GET /api/upcoming?count=5 should accept count parameter."""
        response = client.get("/api/upcoming?count=5")
        assert response.status_code == 200


class TestHotspotStatusEndpoint:
    """Tests for the hotspot status endpoint."""

    def test_hotspot_status(self, client: TestClient):
        """GET /api/hotspot/status should return status."""
        response = client.get("/api/hotspot/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data


class TestConfigEndpointExtended:
    """Extended tests for config endpoint edge cases."""

    def test_update_multiple_fields(self, client: TestClient):
        """POST /api/config should update multiple fields at once."""
        response = client.post(
            "/api/config",
            json={
                "mac_mode": "fixed",
                "fixed_character_index": 10,
            },
        )
        assert response.status_code == 200

    def test_update_empty_request(self, client: TestClient):
        """POST /api/config with empty body should succeed."""
        response = client.post("/api/config", json={})
        assert response.status_code == 200

    def test_update_config_invalid_json(self, client: TestClient):
        """POST /api/config with invalid JSON should fail gracefully."""
        response = client.post(
            "/api/config",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422  # Unprocessable entity


class TestCharacterEndpointsExtended:
    """Extended tests for character endpoints."""

    def test_list_characters_with_all_filters(self, client: TestClient):
        """GET /api/characters with combined filters."""
        # First exclude a character
        client.post("/api/characters/0/exclude")

        # Now search with filters
        response = client.get("/api/characters?search=mame&available_only=true")
        assert response.status_code == 200

    def test_get_character_with_season(self, client: TestClient):
        """GET /api/characters/{index} should show season if applicable."""
        # Find a seasonal character (if any)
        response = client.get("/api/characters")
        chars = response.json()

        # Look for any character with a season
        seasonal = [c for c in chars if c.get("season")]
        if seasonal:
            char = seasonal[0]
            response = client.get(f"/api/characters/{char['index']}")
            assert response.status_code == 200
            assert "season" in response.json()


class TestSSIDEndpointsExtended:
    """Extended tests for SSID endpoints."""

    def test_get_ssid_with_notes(self, client: TestClient):
        """GET /api/ssids/{index} should include notes."""
        response = client.get("/api/ssids/0")
        assert response.status_code == 200
        data = response.json()
        assert "notes" in data

    def test_list_ssids_with_search(self, client: TestClient):
        """GET /api/ssids should work (no search param for SSIDs currently)."""
        response = client.get("/api/ssids")
        assert response.status_code == 200


class TestExclusionIntegration:
    """Integration tests for exclusion system."""

    def test_exclude_then_check_status(self, client: TestClient):
        """Excluding characters should update status counts."""
        # Get initial status
        initial = client.get("/api/status").json()
        initial_excluded = initial["excluded_characters"]

        # Exclude a character
        client.post("/api/characters/0/exclude")

        # Check status updated
        updated = client.get("/api/status").json()
        assert updated["excluded_characters"] == initial_excluded + 1

    def test_clear_all_exclusions_clears_both(self, client: TestClient):
        """DELETE /api/all-exclusions should clear both types."""
        # Exclude both types
        client.post("/api/characters/0/exclude")
        client.post("/api/ssids/0/exclude")

        # Clear all
        response = client.delete("/api/all-exclusions")
        assert response.status_code == 200

        # Verify both cleared
        char_excl = client.get("/api/exclusions").json()
        ssid_excl = client.get("/api/ssid-exclusions").json()

        assert char_excl["excluded_count"] == 0
        assert ssid_excl["excluded_count"] == 0


class TestStatusSpecialModes:
    """Tests for status endpoint in different modes."""

    def test_status_special_ssid_mode(self, client: TestClient):
        """Status should reflect special SSID mode."""
        # Set to special SSID mode
        client.post("/api/config", json={"ssid_mode": "special", "special_ssid_index": 0})

        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "ssid_mode" in data
        # After setting special, check the status reflects it
        assert data["ssid_mode"] == "special"

    def test_status_cycle_mode(self, client: TestClient):
        """Status should work in cycle mode."""
        client.post("/api/config", json={"mac_mode": "cycle"})

        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["mac_mode"] == "cycle"


class TestUpcomingCycleMode:
    """Tests for upcoming endpoint in cycle mode."""

    def test_upcoming_in_cycle_mode(self, client: TestClient):
        """GET /api/upcoming should return characters in cycle mode."""
        # Set to cycle mode
        client.post("/api/config", json={"mac_mode": "cycle"})

        response = client.get("/api/upcoming")
        assert response.status_code == 200
        data = response.json()
        # Should have upcoming characters
        assert isinstance(data, list)

    def test_upcoming_count_in_cycle_mode(self, client: TestClient):
        """GET /api/upcoming?count=3 should return limited list."""
        client.post("/api/config", json={"mac_mode": "cycle"})

        response = client.get("/api/upcoming?count=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3


class TestCharacterIncludeErrors:
    """Tests for include endpoint error handling."""

    def test_include_character_already_included(self, client: TestClient):
        """POST /api/characters/{index}/include on non-excluded should work."""
        # Include a character that's not excluded
        response = client.post("/api/characters/0/include")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_include_ssid_already_included(self, client: TestClient):
        """POST /api/ssids/{index}/include on non-excluded should work."""
        response = client.post("/api/ssids/0/include")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestDebugEndpointComplete:
    """Comprehensive tests for debug endpoint."""

    def test_debug_info_all_fields(self, client: TestClient):
        """GET /api/debug should return complete debug info."""
        response = client.get("/api/debug")
        assert response.status_code == 200
        data = response.json()

        # Check all expected sections exist
        assert "config" in data
        assert "selection" in data
        assert "exclusions" in data
        assert "system" in data
        assert "processes" in data
        assert "network" in data
        assert "services" in data

    def test_debug_selection_info(self, client: TestClient):
        """Debug selection info should be populated."""
        response = client.get("/api/debug")
        data = response.json()

        selection = data["selection"]
        # Should have character info
        assert isinstance(selection, dict)
        assert "character_name" in selection
        assert "is_special_ssid" in selection

    def test_debug_exclusions_info(self, client: TestClient):
        """Debug exclusions info should have counts."""
        response = client.get("/api/debug")
        data = response.json()

        exclusions = data["exclusions"]
        assert "excluded_character_count" in exclusions
        assert "excluded_ssid_count" in exclusions
