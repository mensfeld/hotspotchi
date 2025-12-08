"""
API routes for Hotspotchi web dashboard.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hotspotchi.characters import CHARACTERS, SPECIAL_SSIDS
from hotspotchi.config import HotspotchiConfig, MacMode, SsidMode, load_config
from hotspotchi.exclusions import get_exclusion_manager
from hotspotchi.hotspot import HotspotManager
from hotspotchi.mac import create_mac_address, format_mac
from hotspotchi.selection import (
    get_seconds_until_midnight,
    get_upcoming_characters,
    select_combined,
)

router = APIRouter()

# Default config file location
DEFAULT_CONFIG_PATH = Path("/etc/hotspotchi/config.yaml")


def _load_initial_config() -> HotspotchiConfig:
    """Load config from file or use defaults."""
    if DEFAULT_CONFIG_PATH.exists():
        return load_config(DEFAULT_CONFIG_PATH)
    return HotspotchiConfig()


# Global config and hotspot manager
_current_config = _load_initial_config()
_hotspot_manager: HotspotManager | None = None


def _get_hotspot_manager() -> HotspotManager:
    """Get or create the global hotspot manager."""
    global _hotspot_manager
    if _hotspot_manager is None:
        _hotspot_manager = HotspotManager(_current_config)
    return _hotspot_manager


def _restart_via_systemd() -> bool:
    """Restart hotspot via systemd service if it's running.

    Returns:
        True if restarted via systemd, False if service not active
    """
    import subprocess

    # Check if systemd service is active
    result = subprocess.run(
        ["systemctl", "is-active", "hotspotchi"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False

    # Save current config to file so CLI picks it up
    _save_current_config()

    # Restart the systemd service
    subprocess.run(["systemctl", "restart", "hotspotchi"], check=False)
    return True


def _save_current_config() -> None:
    """Save current config to the config file, preserving existing settings."""
    import yaml

    config_path = Path("/etc/hotspotchi/config.yaml")

    # Read existing config to preserve settings we don't manage
    existing_config: dict[str, object] = {}
    if config_path.exists():
        with open(config_path) as f:
            existing_config = yaml.safe_load(f) or {}

    # Only update the fields that the web UI manages
    # (character selection, SSID mode, etc.)
    updates = {
        "mac_mode": _current_config.mac_mode.value,
        "ssid_mode": _current_config.ssid_mode.value,
        "fixed_character_index": _current_config.fixed_character_index,
        "special_ssid_index": _current_config.special_ssid_index,
    }

    # Merge updates into existing config
    existing_config.update(updates)

    with open(config_path, "w") as f:
        yaml.safe_dump(existing_config, f, default_flow_style=False)


def _is_root() -> bool:
    """Check if running with root privileges."""
    return os.geteuid() == 0


class StatusResponse(BaseModel):
    """Current hotspot status."""

    ssid: str
    mac_address: str | None
    character_name: str | None
    mac_mode: str
    ssid_mode: str
    next_change_at: datetime | None
    seconds_until_change: int | None
    total_characters: int
    available_characters: int
    excluded_characters: int
    total_special_ssids: int
    hotspot_running: bool
    is_root: bool
    fixed_character_index: int
    special_ssid_index: int


class CharacterResponse(BaseModel):
    """Character information."""

    index: int
    name: str
    byte1: int
    byte2: int
    mac_address: str
    season: str | None
    excluded: bool


class SpecialSSIDResponse(BaseModel):
    """Special SSID information."""

    index: int
    ssid: str
    character_name: str
    notes: str
    active: bool
    excluded: bool


class UpcomingCharacter(BaseModel):
    """Upcoming character in cycle mode."""

    position: int
    name: str
    mac_address: str


class ConfigUpdate(BaseModel):
    """Configuration update request."""

    mac_mode: str | None = None
    ssid_mode: str | None = None
    special_ssid_index: int | None = None
    fixed_character_index: int | None = None
    custom_ssid: str | None = None


@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Get current hotspot status."""
    config = _current_config
    manager = _get_hotspot_manager()
    exclusion_manager = get_exclusion_manager()

    # Use combined selection which includes special SSIDs in the rotation
    selection = select_combined(config)

    # Determine SSID, MAC, and character name based on selection
    if selection.is_special_ssid:
        ssid = selection.ssid or config.default_ssid
        mac_address = None
        char_name = selection.name
    elif selection.character:
        ssid = config.default_ssid
        mac_address = format_mac(create_mac_address(selection.character))
        char_name = selection.character.name
    else:
        ssid = config.default_ssid
        mac_address = None
        char_name = None

    # Calculate next change time for daily mode
    next_change = None
    seconds_remaining = None
    if config.mac_mode == MacMode.DAILY_RANDOM:
        seconds_remaining = get_seconds_until_midnight()
        next_change = datetime.now() + timedelta(seconds=seconds_remaining)

    # Count available vs excluded
    excluded_count = exclusion_manager.get_excluded_count()
    available_count = len(CHARACTERS) - excluded_count

    return StatusResponse(
        ssid=ssid,
        mac_address=mac_address,
        character_name=char_name,
        mac_mode=config.mac_mode.value,
        ssid_mode=config.ssid_mode.value,
        next_change_at=next_change,
        seconds_until_change=seconds_remaining,
        total_characters=len(CHARACTERS),
        available_characters=available_count,
        excluded_characters=excluded_count,
        total_special_ssids=len(SPECIAL_SSIDS),
        hotspot_running=manager.is_running(),
        is_root=_is_root(),
        fixed_character_index=config.fixed_character_index,
        special_ssid_index=config.special_ssid_index,
    )


@router.get("/characters", response_model=list[CharacterResponse])
async def list_characters(
    season: str | None = None,
    search: str | None = None,
    excluded_only: bool = False,
    available_only: bool = False,
) -> list[CharacterResponse]:
    """List all MAC-based characters."""
    exclusion_manager = get_exclusion_manager()
    result = []
    for i, char in enumerate(CHARACTERS):
        is_excluded = exclusion_manager.is_excluded(i)

        # Filter by exclusion status
        if excluded_only and not is_excluded:
            continue
        if available_only and is_excluded:
            continue

        # Filter by season
        if season and char.season != season.lower():
            continue

        # Filter by search
        if search and search.lower() not in char.name.lower():
            continue

        result.append(
            CharacterResponse(
                index=i,
                name=char.name,
                byte1=char.byte1,
                byte2=char.byte2,
                mac_address=format_mac(create_mac_address(char)),
                season=char.season,
                excluded=is_excluded,
            )
        )

    return result


@router.get("/characters/{index}", response_model=CharacterResponse)
async def get_character(index: int) -> CharacterResponse:
    """Get a specific character by index."""
    if not 0 <= index < len(CHARACTERS):
        raise HTTPException(status_code=404, detail="Character not found")

    exclusion_manager = get_exclusion_manager()
    char = CHARACTERS[index]
    return CharacterResponse(
        index=index,
        name=char.name,
        byte1=char.byte1,
        byte2=char.byte2,
        mac_address=format_mac(create_mac_address(char)),
        season=char.season,
        excluded=exclusion_manager.is_excluded(index),
    )


@router.get("/ssids", response_model=list[SpecialSSIDResponse])
async def list_ssids(
    active_only: bool = False,
    excluded_only: bool = False,
    available_only: bool = False,
) -> list[SpecialSSIDResponse]:
    """List all special SSID characters."""
    exclusion_manager = get_exclusion_manager()
    result = []
    for i, ssid in enumerate(SPECIAL_SSIDS):
        is_excluded = exclusion_manager.is_ssid_excluded(i)

        if active_only and not ssid.active:
            continue
        if excluded_only and not is_excluded:
            continue
        if available_only and is_excluded:
            continue

        result.append(
            SpecialSSIDResponse(
                index=i,
                ssid=ssid.ssid,
                character_name=ssid.character_name,
                notes=ssid.notes,
                active=ssid.active,
                excluded=is_excluded,
            )
        )

    return result


@router.get("/ssids/{index}", response_model=SpecialSSIDResponse)
async def get_ssid(index: int) -> SpecialSSIDResponse:
    """Get a specific special SSID by index."""
    if not 0 <= index < len(SPECIAL_SSIDS):
        raise HTTPException(status_code=404, detail="SSID not found")

    exclusion_manager = get_exclusion_manager()
    ssid = SPECIAL_SSIDS[index]
    return SpecialSSIDResponse(
        index=index,
        ssid=ssid.ssid,
        character_name=ssid.character_name,
        notes=ssid.notes,
        active=ssid.active,
        excluded=exclusion_manager.is_ssid_excluded(index),
    )


@router.get("/upcoming", response_model=list[UpcomingCharacter])
async def get_upcoming(count: int = 7) -> list[UpcomingCharacter]:
    """Get upcoming characters for cycle mode."""
    config = _current_config

    if config.mac_mode != MacMode.CYCLE:
        return []

    upcoming = get_upcoming_characters(config, count=count)

    return [
        UpcomingCharacter(
            position=i + 1,
            name=char.name,
            mac_address=format_mac(create_mac_address(char)),
        )
        for i, char in enumerate(upcoming)
    ]


@router.post("/config")
async def update_config(update: ConfigUpdate) -> dict:
    """Update configuration."""
    global _current_config

    config_dict = _current_config.model_dump()

    if update.mac_mode:
        try:
            new_mode = MacMode(update.mac_mode)
            config_dict["mac_mode"] = new_mode
            # Reset ssid_mode to NORMAL when switching to rotation modes
            # This prevents stuck special SSID selection from previous fixed mode
            if new_mode in (MacMode.DAILY_RANDOM, MacMode.RANDOM, MacMode.CYCLE):
                config_dict["ssid_mode"] = SsidMode.NORMAL
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid mac_mode: {update.mac_mode}"
            ) from None

    if update.ssid_mode:
        try:
            config_dict["ssid_mode"] = SsidMode(update.ssid_mode)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid ssid_mode: {update.ssid_mode}"
            ) from None

    if update.special_ssid_index is not None:
        if not 0 <= update.special_ssid_index < len(SPECIAL_SSIDS):
            raise HTTPException(status_code=400, detail="Invalid special_ssid_index")
        config_dict["special_ssid_index"] = update.special_ssid_index

    if update.fixed_character_index is not None:
        if not 0 <= update.fixed_character_index < len(CHARACTERS):
            raise HTTPException(status_code=400, detail="Invalid fixed_character_index")
        config_dict["fixed_character_index"] = update.fixed_character_index

    if update.custom_ssid is not None:
        config_dict["custom_ssid"] = update.custom_ssid

    _current_config = HotspotchiConfig(**config_dict)

    # Save config to file so changes persist across restarts
    import contextlib

    with contextlib.suppress(OSError):
        _save_current_config()

    return {"status": "ok", "message": "Configuration updated"}


@router.post("/character/{index}")
async def set_character(index: int, apply: bool = False) -> dict:
    """Set a specific character (updates fixed_character_index without changing mode).

    Args:
        index: Character index to set
        apply: If True and running as root, restart hotspot to apply changes
    """
    global _current_config

    if not 0 <= index < len(CHARACTERS):
        raise HTTPException(status_code=400, detail="Invalid character index")

    # Update character index and set mode to fixed, reset ssid_mode to normal
    _current_config = HotspotchiConfig(
        **{
            **_current_config.model_dump(),
            "mac_mode": MacMode.FIXED,
            "ssid_mode": SsidMode.NORMAL,
            "fixed_character_index": index,
        }
    )

    char = CHARACTERS[index]
    applied = False

    if apply and _is_root():
        # Try systemd first, fall back to direct restart
        if _restart_via_systemd():
            applied = True
        else:
            manager = _get_hotspot_manager()
            if manager.is_running():
                manager.restart(_current_config)
                applied = True

    return {
        "status": "ok",
        "character": char.name,
        "mac_address": format_mac(create_mac_address(char)),
        "applied": applied,
    }


@router.post("/ssid/{index}")
async def set_ssid(index: int, apply: bool = False) -> dict:
    """Set a specific special SSID.

    Args:
        index: SSID index to set
        apply: If True and running as root, restart hotspot to apply changes
    """
    global _current_config

    if not 0 <= index < len(SPECIAL_SSIDS):
        raise HTTPException(status_code=400, detail="Invalid SSID index")

    _current_config = HotspotchiConfig(
        **{
            **_current_config.model_dump(),
            "ssid_mode": SsidMode.SPECIAL,
            "special_ssid_index": index,
        }
    )

    ssid = SPECIAL_SSIDS[index]
    applied = False

    if apply and _is_root():
        # Try systemd first, fall back to direct restart
        if _restart_via_systemd():
            applied = True
        else:
            manager = _get_hotspot_manager()
            if manager.is_running():
                manager.restart(_current_config)
                applied = True

    return {
        "status": "ok",
        "character": ssid.character_name,
        "ssid": ssid.ssid,
        "applied": applied,
    }


@router.post("/hotspot/start")
async def start_hotspot() -> dict:
    """Start the WiFi hotspot."""
    if not _is_root():
        raise HTTPException(
            status_code=403,
            detail="Must run as root to control hotspot. Use: sudo hotspotchi-web",
        )

    manager = _get_hotspot_manager()
    if manager.is_running():
        return {"status": "ok", "message": "Hotspot already running"}

    try:
        manager.update_config(_current_config)
        state = manager.start()
        return {
            "status": "ok",
            "message": "Hotspot started",
            "ssid": state.ssid,
            "mac_address": state.mac_address,
            "character": state.character_name,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/hotspot/stop")
async def stop_hotspot() -> dict:
    """Stop the WiFi hotspot."""
    if not _is_root():
        raise HTTPException(
            status_code=403,
            detail="Must run as root to control hotspot. Use: sudo hotspotchi-web",
        )

    manager = _get_hotspot_manager()
    if not manager.is_running():
        return {"status": "ok", "message": "Hotspot not running"}

    manager.stop()
    return {"status": "ok", "message": "Hotspot stopped"}


@router.post("/hotspot/restart")
async def restart_hotspot() -> dict:
    """Restart the WiFi hotspot with current configuration."""
    if not _is_root():
        raise HTTPException(
            status_code=403,
            detail="Must run as root to control hotspot. Use: sudo hotspotchi-web",
        )

    # Try systemd first, fall back to direct restart
    if _restart_via_systemd():
        return {
            "status": "ok",
            "message": "Hotspot restarted via systemd",
        }

    manager = _get_hotspot_manager()

    try:
        state = manager.restart(_current_config)
        return {
            "status": "ok",
            "message": "Hotspot restarted",
            "ssid": state.ssid,
            "mac_address": state.mac_address,
            "character": state.character_name,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/hotspot/status")
async def get_hotspot_status() -> dict:
    """Get current hotspot running status."""
    manager = _get_hotspot_manager()
    state = manager.get_state()

    return {
        "running": state.running,
        "ssid": state.ssid,
        "mac_address": state.mac_address,
        "character": state.character_name,
        "ip_address": state.ip_address,
        "is_root": _is_root(),
    }


# ============================================
# Character Exclusion Endpoints
# ============================================


@router.post("/characters/{index}/exclude")
async def exclude_character(index: int) -> dict:
    """Exclude a character from rotation modes."""
    if not 0 <= index < len(CHARACTERS):
        raise HTTPException(status_code=404, detail="Character not found")

    exclusion_manager = get_exclusion_manager()
    exclusion_manager.exclude(index)
    char = CHARACTERS[index]

    return {
        "status": "ok",
        "action": "excluded",
        "character": char.name,
        "index": index,
    }


@router.post("/characters/{index}/include")
async def include_character(index: int) -> dict:
    """Include a previously excluded character in rotation modes."""
    if not 0 <= index < len(CHARACTERS):
        raise HTTPException(status_code=404, detail="Character not found")

    exclusion_manager = get_exclusion_manager()
    exclusion_manager.include(index)
    char = CHARACTERS[index]

    return {
        "status": "ok",
        "action": "included",
        "character": char.name,
        "index": index,
    }


@router.post("/characters/{index}/toggle-exclusion")
async def toggle_character_exclusion(index: int) -> dict:
    """Toggle exclusion status for a character."""
    if not 0 <= index < len(CHARACTERS):
        raise HTTPException(status_code=404, detail="Character not found")

    exclusion_manager = get_exclusion_manager()
    is_now_excluded = exclusion_manager.toggle(index)
    char = CHARACTERS[index]

    return {
        "status": "ok",
        "action": "excluded" if is_now_excluded else "included",
        "character": char.name,
        "index": index,
        "excluded": is_now_excluded,
    }


@router.get("/exclusions")
async def get_exclusions() -> dict:
    """Get all excluded character indices."""
    exclusion_manager = get_exclusion_manager()
    excluded = exclusion_manager.get_excluded()

    return {
        "excluded_indices": sorted(excluded),
        "excluded_count": len(excluded),
        "total_characters": len(CHARACTERS),
        "available_count": len(CHARACTERS) - len(excluded),
    }


@router.delete("/exclusions")
async def clear_exclusions() -> dict:
    """Clear all exclusions (include all characters)."""
    exclusion_manager = get_exclusion_manager()
    exclusion_manager.clear()

    return {
        "status": "ok",
        "message": "All characters are now included in rotation",
    }


# ============================================
# Special SSID Exclusion Endpoints
# ============================================


@router.post("/ssids/{index}/exclude")
async def exclude_ssid(index: int) -> dict:
    """Exclude a special SSID from rotation modes."""
    if not 0 <= index < len(SPECIAL_SSIDS):
        raise HTTPException(status_code=404, detail="SSID not found")

    exclusion_manager = get_exclusion_manager()
    exclusion_manager.exclude_ssid(index)
    ssid = SPECIAL_SSIDS[index]

    return {
        "status": "ok",
        "action": "excluded",
        "character": ssid.character_name,
        "index": index,
    }


@router.post("/ssids/{index}/include")
async def include_ssid(index: int) -> dict:
    """Include a previously excluded special SSID in rotation modes."""
    if not 0 <= index < len(SPECIAL_SSIDS):
        raise HTTPException(status_code=404, detail="SSID not found")

    exclusion_manager = get_exclusion_manager()
    exclusion_manager.include_ssid(index)
    ssid = SPECIAL_SSIDS[index]

    return {
        "status": "ok",
        "action": "included",
        "character": ssid.character_name,
        "index": index,
    }


@router.post("/ssids/{index}/toggle-exclusion")
async def toggle_ssid_exclusion(index: int) -> dict:
    """Toggle exclusion status for a special SSID."""
    if not 0 <= index < len(SPECIAL_SSIDS):
        raise HTTPException(status_code=404, detail="SSID not found")

    exclusion_manager = get_exclusion_manager()
    is_now_excluded = exclusion_manager.toggle_ssid(index)
    ssid = SPECIAL_SSIDS[index]

    return {
        "status": "ok",
        "action": "excluded" if is_now_excluded else "included",
        "character": ssid.character_name,
        "index": index,
        "excluded": is_now_excluded,
    }


@router.get("/ssid-exclusions")
async def get_ssid_exclusions() -> dict:
    """Get all excluded special SSID indices."""
    exclusion_manager = get_exclusion_manager()
    excluded = exclusion_manager.get_excluded_ssids()
    active_count = sum(1 for s in SPECIAL_SSIDS if s.active)

    return {
        "excluded_indices": sorted(excluded),
        "excluded_count": len(excluded),
        "total_ssids": len(SPECIAL_SSIDS),
        "active_ssids": active_count,
        "available_count": active_count - len(excluded),
    }


@router.delete("/ssid-exclusions")
async def clear_ssid_exclusions() -> dict:
    """Clear all special SSID exclusions."""
    exclusion_manager = get_exclusion_manager()
    exclusion_manager.clear_ssids()

    return {
        "status": "ok",
        "message": "All special SSIDs are now included in rotation",
    }


@router.delete("/all-exclusions")
async def clear_all_exclusions() -> dict:
    """Clear all exclusions (both characters and special SSIDs)."""
    exclusion_manager = get_exclusion_manager()
    exclusion_manager.clear_all()

    return {
        "status": "ok",
        "message": "All characters and special SSIDs are now included in rotation",
    }


# ============================================
# Debug Endpoint
# ============================================


@router.get("/debug")
async def get_debug_info() -> dict:
    """Get comprehensive debug information for troubleshooting.

    Returns system status, config, processes, and more.
    """
    import subprocess
    from pathlib import Path

    config = _current_config
    exclusion_manager = get_exclusion_manager()
    selection = select_combined(config)

    # Get system process info
    def run_cmd(cmd: list[str]) -> str:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.stdout.strip() or result.stderr.strip()
        except Exception as e:
            return f"Error: {e}"

    # Gather debug info
    debug_info = {
        "config": {
            "wifi_interface": config.wifi_interface,
            "concurrent_mode": config.concurrent_mode,
            "ap_interface": config.ap_interface,
            "ssid_mode": config.ssid_mode.value,
            "mac_mode": config.mac_mode.value,
            "default_ssid": config.default_ssid,
            "fixed_character_index": config.fixed_character_index,
            "special_ssid_index": config.special_ssid_index,
            "include_special_ssids": config.include_special_ssids,
            "ap_ip": config.ap_ip,
            "web_host": config.web_host,
            "web_port": config.web_port,
        },
        "selection": {
            "character_name": selection.name,
            "is_special_ssid": selection.is_special_ssid,
            "ssid": selection.ssid if selection.is_special_ssid else config.default_ssid,
            "mac_address": format_mac(create_mac_address(selection.character))
            if selection.character
            else None,
        },
        "exclusions": {
            "excluded_character_count": exclusion_manager.get_excluded_count(),
            "excluded_character_indices": sorted(exclusion_manager.get_excluded()),
            "excluded_ssid_count": exclusion_manager.get_excluded_ssid_count(),
            "excluded_ssid_indices": sorted(exclusion_manager.get_excluded_ssids()),
        },
        "system": {
            "is_root": _is_root(),
            "config_file_exists": Path("/etc/hotspotchi/config.yaml").exists(),
            "exclusions_file_exists": Path("/var/lib/hotspotchi/exclusions.json").exists(),
        },
        "processes": {
            "hostapd_running": run_cmd(["pgrep", "-x", "hostapd"]) != "",
            "hostapd_pids": run_cmd(["pgrep", "-x", "hostapd"]),
            "dnsmasq_running": run_cmd(["pgrep", "dnsmasq"]) != "",
            "dnsmasq_pids": run_cmd(["pgrep", "dnsmasq"]),
        },
        "network": {
            "interfaces": run_cmd(["ip", "-br", "link"]),
            "wifi_interface_info": run_cmd(["ip", "addr", "show", config.wifi_interface]),
        },
        "services": {
            "hotspotchi_status": run_cmd(["systemctl", "is-active", "hotspotchi"]),
            "hotspotchi_web_status": run_cmd(["systemctl", "is-active", "hotspotchi-web"]),
        },
    }

    # Read config file content if it exists
    config_path = Path("/etc/hotspotchi/config.yaml")
    if config_path.exists():
        try:
            debug_info["config_file_content"] = config_path.read_text()
        except Exception as e:
            debug_info["config_file_content"] = f"Error reading: {e}"

    return debug_info
