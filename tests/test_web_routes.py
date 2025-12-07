"""Tests for web API routes, focusing on SSID exclusion endpoints."""

import pytest
from fastapi.testclient import TestClient

from hotspotchi.characters import SPECIAL_SSIDS
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
