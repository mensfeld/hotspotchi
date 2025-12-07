"""
API routes for HotSpotchi web dashboard.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hotspotchi.characters import CHARACTERS, SPECIAL_SSIDS
from hotspotchi.config import HotSpotchiConfig, MacMode, SsidMode
from hotspotchi.mac import create_mac_address, format_mac
from hotspotchi.selection import (
    get_seconds_until_midnight,
    get_upcoming_characters,
    select_character,
)
from hotspotchi.ssid import resolve_ssid

router = APIRouter()

# Global config (in production, this would be persisted)
_current_config = HotSpotchiConfig()


class StatusResponse(BaseModel):
    """Current hotspot status."""

    ssid: str
    mac_address: Optional[str]
    character_name: Optional[str]
    mac_mode: str
    ssid_mode: str
    next_change_at: Optional[datetime]
    seconds_until_change: Optional[int]
    total_characters: int
    total_special_ssids: int


class CharacterResponse(BaseModel):
    """Character information."""

    index: int
    name: str
    byte1: int
    byte2: int
    mac_address: str
    season: Optional[str]


class SpecialSSIDResponse(BaseModel):
    """Special SSID information."""

    index: int
    ssid: str
    character_name: str
    notes: str
    active: bool


class UpcomingCharacter(BaseModel):
    """Upcoming character in cycle mode."""

    position: int
    name: str
    mac_address: str


class ConfigUpdate(BaseModel):
    """Configuration update request."""

    mac_mode: Optional[str] = None
    ssid_mode: Optional[str] = None
    special_ssid_index: Optional[int] = None
    fixed_character_index: Optional[int] = None
    custom_ssid: Optional[str] = None


@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Get current hotspot status."""
    config = _current_config

    ssid, special_char = resolve_ssid(config)
    character = select_character(config)

    mac_address = format_mac(create_mac_address(character)) if character else None
    char_name = special_char or (character.name if character else None)

    # Calculate next change time for daily mode
    next_change = None
    seconds_remaining = None
    if config.mac_mode == MacMode.DAILY_RANDOM:
        seconds_remaining = get_seconds_until_midnight()
        next_change = datetime.now() + timedelta(seconds=seconds_remaining)

    return StatusResponse(
        ssid=ssid,
        mac_address=mac_address,
        character_name=char_name,
        mac_mode=config.mac_mode.value,
        ssid_mode=config.ssid_mode.value,
        next_change_at=next_change,
        seconds_until_change=seconds_remaining,
        total_characters=len(CHARACTERS),
        total_special_ssids=len(SPECIAL_SSIDS),
    )


@router.get("/characters", response_model=list[CharacterResponse])
async def list_characters(
    season: Optional[str] = None,
    search: Optional[str] = None,
) -> list[CharacterResponse]:
    """List all MAC-based characters."""
    result = []
    for i, char in enumerate(CHARACTERS):
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
            )
        )

    return result


@router.get("/characters/{index}", response_model=CharacterResponse)
async def get_character(index: int) -> CharacterResponse:
    """Get a specific character by index."""
    if not 0 <= index < len(CHARACTERS):
        raise HTTPException(status_code=404, detail="Character not found")

    char = CHARACTERS[index]
    return CharacterResponse(
        index=index,
        name=char.name,
        byte1=char.byte1,
        byte2=char.byte2,
        mac_address=format_mac(create_mac_address(char)),
        season=char.season,
    )


@router.get("/ssids", response_model=list[SpecialSSIDResponse])
async def list_ssids(active_only: bool = False) -> list[SpecialSSIDResponse]:
    """List all special SSID characters."""
    result = []
    for i, ssid in enumerate(SPECIAL_SSIDS):
        if active_only and not ssid.active:
            continue

        result.append(
            SpecialSSIDResponse(
                index=i,
                ssid=ssid.ssid,
                character_name=ssid.character_name,
                notes=ssid.notes,
                active=ssid.active,
            )
        )

    return result


@router.get("/ssids/{index}", response_model=SpecialSSIDResponse)
async def get_ssid(index: int) -> SpecialSSIDResponse:
    """Get a specific special SSID by index."""
    if not 0 <= index < len(SPECIAL_SSIDS):
        raise HTTPException(status_code=404, detail="SSID not found")

    ssid = SPECIAL_SSIDS[index]
    return SpecialSSIDResponse(
        index=index,
        ssid=ssid.ssid,
        character_name=ssid.character_name,
        notes=ssid.notes,
        active=ssid.active,
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
            config_dict["mac_mode"] = MacMode(update.mac_mode)
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

    _current_config = HotSpotchiConfig(**config_dict)

    return {"status": "ok", "message": "Configuration updated"}


@router.post("/character/{index}")
async def set_character(index: int) -> dict:
    """Set a specific character (switches to fixed mode)."""
    global _current_config

    if not 0 <= index < len(CHARACTERS):
        raise HTTPException(status_code=400, detail="Invalid character index")

    _current_config = HotSpotchiConfig(
        **{
            **_current_config.model_dump(),
            "mac_mode": MacMode.FIXED,
            "fixed_character_index": index,
        }
    )

    char = CHARACTERS[index]
    return {
        "status": "ok",
        "character": char.name,
        "mac_address": format_mac(create_mac_address(char)),
    }


@router.post("/ssid/{index}")
async def set_ssid(index: int) -> dict:
    """Set a specific special SSID."""
    global _current_config

    if not 0 <= index < len(SPECIAL_SSIDS):
        raise HTTPException(status_code=400, detail="Invalid SSID index")

    _current_config = HotSpotchiConfig(
        **{
            **_current_config.model_dump(),
            "ssid_mode": SsidMode.SPECIAL,
            "special_ssid_index": index,
        }
    )

    ssid = SPECIAL_SSIDS[index]
    return {
        "status": "ok",
        "character": ssid.character_name,
        "ssid": ssid.ssid,
    }
