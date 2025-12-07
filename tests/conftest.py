"""Pytest configuration and fixtures."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from hotspotchi.config import HotSpotchiConfig, MacMode, SsidMode


@pytest.fixture
def default_config() -> HotSpotchiConfig:
    """Provide default configuration for tests."""
    return HotSpotchiConfig()


@pytest.fixture
def temp_dir():
    """Provide a temporary directory."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_cycle_file(temp_dir: Path) -> Path:
    """Provide a temporary file for cycle index testing."""
    cycle_file = temp_dir / "cycle.txt"
    cycle_file.write_text("0")
    return cycle_file


@pytest.fixture
def fixed_config() -> HotSpotchiConfig:
    """Configuration for fixed character mode."""
    return HotSpotchiConfig(
        mac_mode=MacMode.FIXED,
        fixed_character_index=5,
    )


@pytest.fixture
def daily_random_config() -> HotSpotchiConfig:
    """Configuration for daily random mode."""
    return HotSpotchiConfig(mac_mode=MacMode.DAILY_RANDOM)


@pytest.fixture
def cycle_config(temp_cycle_file: Path) -> HotSpotchiConfig:
    """Configuration for cycle mode with temp file."""
    return HotSpotchiConfig(
        mac_mode=MacMode.CYCLE,
        cycle_file=temp_cycle_file,
    )


@pytest.fixture
def special_ssid_config() -> HotSpotchiConfig:
    """Configuration for special SSID mode."""
    return HotSpotchiConfig(
        ssid_mode=SsidMode.SPECIAL,
        special_ssid_index=0,
    )


@pytest.fixture
def custom_ssid_config() -> HotSpotchiConfig:
    """Configuration for custom SSID mode."""
    return HotSpotchiConfig(
        ssid_mode=SsidMode.CUSTOM,
        custom_ssid="MyCustomNetwork",
    )
