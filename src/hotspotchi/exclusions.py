"""
Character exclusion management for Hotspotchi.

Allows users to exclude specific characters from rotation modes,
keeping some discovery aspect of the game.

Supports both MAC-based characters (indices 0-68) and special SSID
characters (indices 0-20 stored separately).
"""

from __future__ import annotations

import json
from pathlib import Path

# Default exclusions file location
DEFAULT_EXCLUSIONS_FILE = Path("/var/lib/hotspotchi/exclusions.json")


class ExclusionManager:
    """Manages excluded character indices for both MAC and special SSID characters."""

    def __init__(self, exclusions_file: Path = DEFAULT_EXCLUSIONS_FILE):
        """Initialize the exclusion manager.

        Args:
            exclusions_file: Path to the JSON file storing exclusions
        """
        self.exclusions_file = exclusions_file
        self._excluded: set[int] = set()
        self._excluded_ssids: set[int] = set()
        self._load()

    def _load(self) -> None:
        """Load exclusions from file."""
        if self.exclusions_file.exists():
            try:
                with open(self.exclusions_file) as f:
                    data = json.load(f)
                    self._excluded = set(data.get("excluded_indices", []))
                    self._excluded_ssids = set(data.get("excluded_ssid_indices", []))
            except (json.JSONDecodeError, OSError):
                self._excluded = set()
                self._excluded_ssids = set()
        else:
            self._excluded = set()
            self._excluded_ssids = set()

    def _save(self) -> None:
        """Save exclusions to file."""
        try:
            self.exclusions_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.exclusions_file, "w") as f:
                json.dump(
                    {
                        "excluded_indices": sorted(self._excluded),
                        "excluded_ssid_indices": sorted(self._excluded_ssids),
                    },
                    f,
                    indent=2,
                )
        except OSError:
            pass  # Best effort - continue even if we can't persist

    def is_excluded(self, index: int) -> bool:
        """Check if a character index is excluded.

        Args:
            index: Character index to check

        Returns:
            True if excluded, False otherwise
        """
        return index in self._excluded

    def exclude(self, index: int) -> None:
        """Exclude a character by index.

        Args:
            index: Character index to exclude
        """
        self._excluded.add(index)
        self._save()

    def include(self, index: int) -> None:
        """Include a previously excluded character.

        Args:
            index: Character index to include
        """
        self._excluded.discard(index)
        self._save()

    def toggle(self, index: int) -> bool:
        """Toggle exclusion status for a character.

        Args:
            index: Character index to toggle

        Returns:
            True if now excluded, False if now included
        """
        if index in self._excluded:
            self._excluded.discard(index)
            self._save()
            return False
        else:
            self._excluded.add(index)
            self._save()
            return True

    def get_excluded(self) -> set[int]:
        """Get all excluded character indices.

        Returns:
            Set of excluded indices
        """
        return self._excluded.copy()

    def get_excluded_count(self) -> int:
        """Get count of excluded characters.

        Returns:
            Number of excluded characters
        """
        return len(self._excluded)

    def clear(self) -> None:
        """Clear all character exclusions."""
        self._excluded.clear()
        self._save()

    def set_excluded(self, indices: set[int]) -> None:
        """Set the excluded indices directly.

        Args:
            indices: Set of indices to exclude
        """
        self._excluded = set(indices)
        self._save()

    # Special SSID exclusion methods

    def is_ssid_excluded(self, index: int) -> bool:
        """Check if a special SSID index is excluded.

        Args:
            index: Special SSID index to check

        Returns:
            True if excluded, False otherwise
        """
        return index in self._excluded_ssids

    def exclude_ssid(self, index: int) -> None:
        """Exclude a special SSID by index.

        Args:
            index: Special SSID index to exclude
        """
        self._excluded_ssids.add(index)
        self._save()

    def include_ssid(self, index: int) -> None:
        """Include a previously excluded special SSID.

        Args:
            index: Special SSID index to include
        """
        self._excluded_ssids.discard(index)
        self._save()

    def toggle_ssid(self, index: int) -> bool:
        """Toggle exclusion status for a special SSID.

        Args:
            index: Special SSID index to toggle

        Returns:
            True if now excluded, False if now included
        """
        if index in self._excluded_ssids:
            self._excluded_ssids.discard(index)
            self._save()
            return False
        else:
            self._excluded_ssids.add(index)
            self._save()
            return True

    def get_excluded_ssids(self) -> set[int]:
        """Get all excluded special SSID indices.

        Returns:
            Set of excluded SSID indices
        """
        return self._excluded_ssids.copy()

    def get_excluded_ssid_count(self) -> int:
        """Get count of excluded special SSIDs.

        Returns:
            Number of excluded special SSIDs
        """
        return len(self._excluded_ssids)

    def clear_ssids(self) -> None:
        """Clear all special SSID exclusions."""
        self._excluded_ssids.clear()
        self._save()

    def clear_all(self) -> None:
        """Clear all exclusions (both characters and special SSIDs)."""
        self._excluded.clear()
        self._excluded_ssids.clear()
        self._save()


# Global exclusion manager instance
_exclusion_manager: ExclusionManager | None = None


def get_exclusion_manager(
    exclusions_file: Path = DEFAULT_EXCLUSIONS_FILE,
) -> ExclusionManager:
    """Get the global exclusion manager instance.

    Args:
        exclusions_file: Path to exclusions file (only used on first call)

    Returns:
        ExclusionManager instance
    """
    global _exclusion_manager
    if _exclusion_manager is None:
        _exclusion_manager = ExclusionManager(exclusions_file)
    return _exclusion_manager


def reset_exclusion_manager() -> None:
    """Reset the global exclusion manager (for testing)."""
    global _exclusion_manager
    _exclusion_manager = None
