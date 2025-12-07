"""Tests for character and SSID exclusion management."""

import json
from pathlib import Path

import pytest

from hotspotchi.exclusions import (
    ExclusionManager,
    get_exclusion_manager,
    reset_exclusion_manager,
)


@pytest.fixture(autouse=True)
def reset_manager():
    """Reset the global exclusion manager before and after each test."""
    reset_exclusion_manager()
    yield
    reset_exclusion_manager()


class TestExclusionManager:
    """Tests for ExclusionManager class."""

    def test_init_creates_empty_sets(self, temp_dir: Path):
        """New manager should have empty exclusion sets."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        assert manager.get_excluded() == set()
        assert manager.get_excluded_ssids() == set()

    def test_exclude_adds_to_set(self, temp_dir: Path):
        """Exclude should add index to excluded set."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        manager.exclude(5)
        assert manager.is_excluded(5)
        assert 5 in manager.get_excluded()

    def test_include_removes_from_set(self, temp_dir: Path):
        """Include should remove index from excluded set."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        manager.exclude(5)
        manager.include(5)
        assert not manager.is_excluded(5)
        assert 5 not in manager.get_excluded()

    def test_include_nonexistent_is_safe(self, temp_dir: Path):
        """Include on non-excluded index should be safe."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        manager.include(5)  # Should not raise
        assert not manager.is_excluded(5)

    def test_toggle_excludes_included(self, temp_dir: Path):
        """Toggle should exclude an included character."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        result = manager.toggle(5)
        assert result is True
        assert manager.is_excluded(5)

    def test_toggle_includes_excluded(self, temp_dir: Path):
        """Toggle should include an excluded character."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        manager.exclude(5)
        result = manager.toggle(5)
        assert result is False
        assert not manager.is_excluded(5)

    def test_get_excluded_returns_copy(self, temp_dir: Path):
        """get_excluded should return a copy, not the original set."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        manager.exclude(5)
        excluded = manager.get_excluded()
        excluded.add(10)  # Modify the copy
        assert not manager.is_excluded(10)  # Original unchanged

    def test_get_excluded_count(self, temp_dir: Path):
        """get_excluded_count should return correct count."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        assert manager.get_excluded_count() == 0
        manager.exclude(1)
        manager.exclude(2)
        manager.exclude(3)
        assert manager.get_excluded_count() == 3

    def test_clear_removes_all(self, temp_dir: Path):
        """Clear should remove all exclusions."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        manager.exclude(1)
        manager.exclude(2)
        manager.exclude(3)
        manager.clear()
        assert manager.get_excluded() == set()
        assert manager.get_excluded_count() == 0

    def test_set_excluded_replaces_all(self, temp_dir: Path):
        """set_excluded should replace all exclusions."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        manager.exclude(1)
        manager.set_excluded({10, 20, 30})
        assert manager.get_excluded() == {10, 20, 30}
        assert not manager.is_excluded(1)


class TestExclusionManagerSSIDs:
    """Tests for SSID exclusion methods."""

    def test_exclude_ssid_adds_to_set(self, temp_dir: Path):
        """Exclude SSID should add index to excluded set."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        manager.exclude_ssid(5)
        assert manager.is_ssid_excluded(5)
        assert 5 in manager.get_excluded_ssids()

    def test_include_ssid_removes_from_set(self, temp_dir: Path):
        """Include SSID should remove index from excluded set."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        manager.exclude_ssid(5)
        manager.include_ssid(5)
        assert not manager.is_ssid_excluded(5)
        assert 5 not in manager.get_excluded_ssids()

    def test_include_ssid_nonexistent_is_safe(self, temp_dir: Path):
        """Include on non-excluded SSID should be safe."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        manager.include_ssid(5)  # Should not raise
        assert not manager.is_ssid_excluded(5)

    def test_toggle_ssid_excludes_included(self, temp_dir: Path):
        """Toggle SSID should exclude an included SSID."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        result = manager.toggle_ssid(5)
        assert result is True
        assert manager.is_ssid_excluded(5)

    def test_toggle_ssid_includes_excluded(self, temp_dir: Path):
        """Toggle SSID should include an excluded SSID."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        manager.exclude_ssid(5)
        result = manager.toggle_ssid(5)
        assert result is False
        assert not manager.is_ssid_excluded(5)

    def test_get_excluded_ssids_returns_copy(self, temp_dir: Path):
        """get_excluded_ssids should return a copy."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        manager.exclude_ssid(5)
        excluded = manager.get_excluded_ssids()
        excluded.add(10)
        assert not manager.is_ssid_excluded(10)

    def test_get_excluded_ssid_count(self, temp_dir: Path):
        """get_excluded_ssid_count should return correct count."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        assert manager.get_excluded_ssid_count() == 0
        manager.exclude_ssid(1)
        manager.exclude_ssid(2)
        assert manager.get_excluded_ssid_count() == 2

    def test_clear_ssids_removes_all(self, temp_dir: Path):
        """clear_ssids should remove all SSID exclusions."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        manager.exclude_ssid(1)
        manager.exclude_ssid(2)
        manager.clear_ssids()
        assert manager.get_excluded_ssids() == set()
        assert manager.get_excluded_ssid_count() == 0


class TestExclusionManagerCombined:
    """Tests for combined character and SSID operations."""

    def test_exclusions_are_separate(self, temp_dir: Path):
        """Character and SSID exclusions should be separate."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        manager.exclude(5)
        manager.exclude_ssid(5)
        assert manager.is_excluded(5)
        assert manager.is_ssid_excluded(5)
        manager.include(5)
        assert not manager.is_excluded(5)
        assert manager.is_ssid_excluded(5)  # SSID still excluded

    def test_clear_all_removes_both(self, temp_dir: Path):
        """clear_all should remove both character and SSID exclusions."""
        manager = ExclusionManager(temp_dir / "exclusions.json")
        manager.exclude(1)
        manager.exclude_ssid(2)
        manager.clear_all()
        assert manager.get_excluded() == set()
        assert manager.get_excluded_ssids() == set()


class TestExclusionManagerPersistence:
    """Tests for file persistence."""

    def test_saves_to_file(self, temp_dir: Path):
        """Exclusions should be saved to file."""
        exclusions_file = temp_dir / "exclusions.json"
        manager = ExclusionManager(exclusions_file)
        manager.exclude(5)
        manager.exclude_ssid(10)

        # Read file directly
        with open(exclusions_file) as f:
            data = json.load(f)
        assert data["excluded_indices"] == [5]
        assert data["excluded_ssid_indices"] == [10]

    def test_loads_from_file(self, temp_dir: Path):
        """Exclusions should be loaded from file."""
        exclusions_file = temp_dir / "exclusions.json"
        exclusions_file.write_text(
            json.dumps(
                {
                    "excluded_indices": [1, 2, 3],
                    "excluded_ssid_indices": [4, 5],
                }
            )
        )

        manager = ExclusionManager(exclusions_file)
        assert manager.get_excluded() == {1, 2, 3}
        assert manager.get_excluded_ssids() == {4, 5}

    def test_handles_missing_file(self, temp_dir: Path):
        """Should handle missing file gracefully."""
        exclusions_file = temp_dir / "nonexistent.json"
        manager = ExclusionManager(exclusions_file)
        assert manager.get_excluded() == set()
        assert manager.get_excluded_ssids() == set()

    def test_handles_corrupted_json(self, temp_dir: Path):
        """Should handle corrupted JSON gracefully."""
        exclusions_file = temp_dir / "exclusions.json"
        exclusions_file.write_text("not valid json {{{")

        manager = ExclusionManager(exclusions_file)
        assert manager.get_excluded() == set()
        assert manager.get_excluded_ssids() == set()

    def test_handles_missing_keys(self, temp_dir: Path):
        """Should handle missing keys in JSON."""
        exclusions_file = temp_dir / "exclusions.json"
        exclusions_file.write_text(json.dumps({}))

        manager = ExclusionManager(exclusions_file)
        assert manager.get_excluded() == set()
        assert manager.get_excluded_ssids() == set()

    def test_creates_parent_directories(self, temp_dir: Path):
        """Should create parent directories when saving."""
        exclusions_file = temp_dir / "subdir" / "nested" / "exclusions.json"
        manager = ExclusionManager(exclusions_file)
        manager.exclude(5)
        assert exclusions_file.exists()


class TestGlobalExclusionManager:
    """Tests for global exclusion manager functions."""

    def test_get_exclusion_manager_returns_instance(self, temp_dir: Path):
        """get_exclusion_manager should return an ExclusionManager."""
        manager = get_exclusion_manager(temp_dir / "exclusions.json")
        assert isinstance(manager, ExclusionManager)

    def test_get_exclusion_manager_returns_same_instance(self, temp_dir: Path):
        """get_exclusion_manager should return the same instance."""
        manager1 = get_exclusion_manager(temp_dir / "exclusions.json")
        manager2 = get_exclusion_manager(temp_dir / "exclusions.json")
        assert manager1 is manager2

    def test_reset_clears_global_instance(self, temp_dir: Path):
        """reset_exclusion_manager should clear the global instance."""
        manager1 = get_exclusion_manager(temp_dir / "exclusions1.json")
        manager1.exclude(5)
        reset_exclusion_manager()
        manager2 = get_exclusion_manager(temp_dir / "exclusions2.json")
        assert manager1 is not manager2
        # New manager should not have the exclusion
        assert not manager2.is_excluded(5)
