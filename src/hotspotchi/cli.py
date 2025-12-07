"""
Command-line interface for HotSpotchi.

Provides commands to start, stop, and manage the WiFi hotspot,
list characters, and configure settings.
"""

from pathlib import Path
from typing import Optional

import click

from hotspotchi import __version__
from hotspotchi.characters import CHARACTERS, SPECIAL_SSIDS
from hotspotchi.config import HotSpotchiConfig, MacMode, SsidMode, load_config
from hotspotchi.hotspot import HotspotManager, run_hotspot
from hotspotchi.mac import create_mac_address, format_mac
from hotspotchi.selection import (
    get_seconds_until_midnight,
    get_upcoming_characters,
    select_character,
)
from hotspotchi.ssid import resolve_ssid

# Default config file location
DEFAULT_CONFIG_PATH = Path("/etc/hotspotchi/config.yaml")


@click.group()
@click.version_option(version=__version__, prog_name="HotSpotchi")
@click.pass_context
def main(ctx: click.Context) -> None:
    """HotSpotchi - Tamagotchi Uni WiFi Hotspot.

    Create WiFi access points to meet Tamagotchi characters!
    """
    ctx.ensure_object(dict)


@main.command()
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=False, path_type=Path),
    default=None,
    help="Path to config file (default: /etc/hotspotchi/config.yaml)",
)
@click.option(
    "--mac-mode",
    type=click.Choice(["daily_random", "random", "cycle", "fixed", "disabled"]),
    default=None,
    help="Character selection mode (overrides config file)",
)
@click.option(
    "--ssid-mode",
    type=click.Choice(["normal", "special", "custom"]),
    default=None,
    help="SSID selection mode (overrides config file)",
)
@click.option("--ssid", default=None, help="Custom SSID (requires --ssid-mode=custom)")
@click.option(
    "--special-index",
    type=int,
    default=None,
    help="Special SSID index (requires --ssid-mode=special)",
)
@click.option(
    "--character-index",
    type=int,
    default=None,
    help="Character index (requires --mac-mode=fixed)",
)
@click.option("--interface", default=None, help="WiFi interface to use")
@click.option("--password", default=None, help="WiFi password (8+ chars for WPA2)")
@click.option(
    "--concurrent/--no-concurrent",
    default=None,
    help="Enable/disable concurrent mode",
)
def start(
    config_path: Optional[Path],
    mac_mode: Optional[str],
    ssid_mode: Optional[str],
    ssid: Optional[str],
    special_index: Optional[int],
    character_index: Optional[int],
    interface: Optional[str],
    password: Optional[str],
    concurrent: Optional[bool],
) -> None:
    """Start the WiFi hotspot.

    The hotspot will run until you press Ctrl+C or send SIGTERM.
    Loads settings from /etc/hotspotchi/config.yaml by default.
    Command-line options override config file settings.
    """
    # Load config from file first
    effective_path = config_path or DEFAULT_CONFIG_PATH
    if effective_path.exists():
        config = load_config(effective_path)
        click.echo(f"Loaded config from {effective_path}")
    else:
        config = HotSpotchiConfig()
        if config_path:
            click.echo(f"Warning: Config file {config_path} not found, using defaults")

    # Override with command-line options
    overrides: dict[str, object] = {}
    if mac_mode is not None:
        overrides["mac_mode"] = MacMode(mac_mode)
    if ssid_mode is not None:
        overrides["ssid_mode"] = SsidMode(ssid_mode)
    if ssid is not None:
        overrides["custom_ssid"] = ssid
    if special_index is not None:
        overrides["special_ssid_index"] = special_index
    if character_index is not None:
        overrides["fixed_character_index"] = character_index
    if interface is not None:
        overrides["wifi_interface"] = interface
    if password is not None:
        overrides["wifi_password"] = password
    if concurrent is not None:
        overrides["concurrent_mode"] = concurrent

    if overrides:
        config = HotSpotchiConfig(**{**config.model_dump(), **overrides})

    # Show concurrent mode status
    if config.concurrent_mode:
        click.echo("Concurrent mode: ENABLED (will create virtual AP interface)")
    else:
        click.echo("Concurrent mode: DISABLED (will take over WiFi interface)")

    run_hotspot(config)


@main.command()
@click.option("--mac-mode", default=None, help="MAC mode to preview (default: from config)")
@click.option("--character-index", type=int, default=None, help="Fixed character index")
def status(mac_mode: Optional[str], character_index: Optional[int]) -> None:
    """Show current/preview character selection."""
    # Load config from file first
    if DEFAULT_CONFIG_PATH.exists():
        config = load_config(DEFAULT_CONFIG_PATH)
    else:
        config = HotSpotchiConfig()

    # Apply overrides if provided
    overrides: dict[str, object] = {}
    if mac_mode is not None:
        overrides["mac_mode"] = MacMode(mac_mode)
    if character_index is not None:
        overrides["fixed_character_index"] = character_index

    if overrides:
        config = HotSpotchiConfig(**{**config.model_dump(), **overrides})

    character = select_character(config)
    ssid, special_char = resolve_ssid(config)

    click.echo("HotSpotchi Status")
    click.echo("=" * 40)
    click.echo(f"MAC Mode: {config.mac_mode.value}")
    click.echo(f"SSID Mode: {config.ssid_mode.value}")
    click.echo(f"SSID: {ssid}")

    if character:
        mac = format_mac(create_mac_address(character))
        click.echo(f"Character: {character.name}")
        click.echo(f"MAC Address: {mac}")
        if character.season:
            click.echo(f"Season: {character.season}")
    elif special_char:
        click.echo(f"Special Character: {special_char}")
    else:
        click.echo("Character: (none - MAC disabled)")

    if config.mac_mode == MacMode.DAILY_RANDOM:
        seconds = get_seconds_until_midnight()
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        click.echo(f"Next change: {hours}h {minutes}m")

    if config.mac_mode == MacMode.CYCLE:
        upcoming = get_upcoming_characters(config, count=5)
        click.echo("\nUpcoming characters:")
        for i, char in enumerate(upcoming, 1):
            click.echo(f"  {i}. {char.name}")


@main.command("list-characters")
@click.option("--season", help="Filter by season (spring/summer/fall/winter)")
@click.option("--search", help="Search characters by name")
def list_characters(season: Optional[str], search: Optional[str]) -> None:
    """List all MAC-based characters."""
    chars = list(CHARACTERS)

    if season:
        chars = [c for c in chars if c.season == season.lower()]

    if search:
        search_lower = search.lower()
        chars = [c for c in chars if search_lower in c.name.lower()]

    click.echo(f"MAC-Based Characters ({len(chars)} total)")
    click.echo("=" * 60)

    for char in chars:
        mac = format_mac(create_mac_address(char))
        season_str = f" [{char.season}]" if char.season else ""
        # Find original index
        orig_idx = CHARACTERS.index(char)
        click.echo(f"[{orig_idx:2d}] {char.name:25s} {mac}{season_str}")


@main.command("list-ssids")
@click.option("--active/--all", default=True, help="Show only active SSIDs")
def list_ssids(active: bool) -> None:
    """List all special SSID characters."""
    click.echo("Special SSID Characters")
    click.echo("=" * 70)

    for i, ssid in enumerate(SPECIAL_SSIDS):
        if active and not ssid.active:
            continue

        status = "" if ssid.active else " [INACTIVE]"
        click.echo(f"\n[{i:2d}] {ssid.character_name}{status}")
        click.echo(f"     SSID: {ssid.ssid}")
        click.echo(f"     Notes: {ssid.notes}")


def _load_base_config() -> HotSpotchiConfig:
    """Load base config from file or use defaults."""
    if DEFAULT_CONFIG_PATH.exists():
        return load_config(DEFAULT_CONFIG_PATH)
    return HotSpotchiConfig()


def _config_with_overrides(**overrides: object) -> HotSpotchiConfig:
    """Load config from file and apply overrides."""
    base = _load_base_config()
    return HotSpotchiConfig(**{**base.model_dump(), **overrides})


@main.command()
def interactive() -> None:
    """Run interactive character selection menu."""
    while True:
        click.echo("\n" + "=" * 50)
        click.echo("  HotSpotchi - Interactive Menu")
        click.echo("=" * 50)
        click.echo("\n[1] List MAC-based characters")
        click.echo("[2] List special SSID characters")
        click.echo("[3] Start with random MAC character")
        click.echo("[4] Start with specific MAC character")
        click.echo("[5] Start with special SSID character")
        click.echo("[6] Start with custom SSID")
        click.echo("[q] Quit")
        click.echo()

        choice = click.prompt("Select option", type=str).strip().lower()

        if choice == "1":
            ctx = click.Context(list_characters)
            ctx.invoke(list_characters)

        elif choice == "2":
            ctx = click.Context(list_ssids)
            ctx.invoke(list_ssids, active=False)

        elif choice == "3":
            config = _config_with_overrides(mac_mode=MacMode.RANDOM)
            run_hotspot(config)

        elif choice == "4":
            ctx = click.Context(list_characters)
            ctx.invoke(list_characters)
            try:
                idx = click.prompt("Enter character number", type=int)
                if 0 <= idx < len(CHARACTERS):
                    config = _config_with_overrides(
                        mac_mode=MacMode.FIXED,
                        fixed_character_index=idx,
                    )
                    run_hotspot(config)
                else:
                    click.echo("Invalid selection")
            except ValueError:
                click.echo("Invalid number")

        elif choice == "5":
            ctx = click.Context(list_ssids)
            ctx.invoke(list_ssids, active=True)
            try:
                idx = click.prompt("Enter SSID number", type=int)
                if 0 <= idx < len(SPECIAL_SSIDS):
                    config = _config_with_overrides(
                        ssid_mode=SsidMode.SPECIAL,
                        special_ssid_index=idx,
                    )
                    run_hotspot(config)
                else:
                    click.echo("Invalid selection")
            except ValueError:
                click.echo("Invalid number")

        elif choice == "6":
            ssid = click.prompt("Enter custom SSID", type=str).strip()
            if ssid:
                config = _config_with_overrides(
                    ssid_mode=SsidMode.CUSTOM,
                    custom_ssid=ssid,
                )
                run_hotspot(config)
            else:
                click.echo("SSID cannot be empty")

        elif choice == "q":
            break


@main.command()
def check() -> None:
    """Check system requirements."""
    # Load config from file if it exists
    if DEFAULT_CONFIG_PATH.exists():
        config = load_config(DEFAULT_CONFIG_PATH)
        click.echo(f"Loaded config from {DEFAULT_CONFIG_PATH}")
    else:
        config = HotSpotchiConfig()
        click.echo("Using default config (no config file found)")

    manager = HotspotManager(config)

    click.echo()
    click.echo("HotSpotchi System Check")
    click.echo("=" * 40)

    # Check root
    if manager.check_root():
        click.echo("[OK] Running as root")
    else:
        click.echo("[!!] Not running as root (use sudo)")

    # Check dependencies
    missing = manager.check_dependencies()
    if missing:
        click.echo(f"[!!] Missing: {', '.join(missing)}")
        click.echo("     Install with: sudo apt install hostapd dnsmasq")
    else:
        click.echo("[OK] All dependencies installed")

    # Check WiFi interface
    interface = config.wifi_interface
    if Path(f"/sys/class/net/{interface}").exists():
        click.echo(f"[OK] Interface {interface} exists")
    else:
        click.echo(f"[!!] Interface {interface} not found")

    # Show concurrent mode status
    if config.concurrent_mode:
        click.echo(f"[--] Concurrent mode: ENABLED (AP interface: {config.ap_interface})")
    else:
        click.echo("[--] Concurrent mode: DISABLED")

    # Summary
    click.echo()
    if not missing and manager.check_root():
        click.echo("Ready to run: sudo hotspotchi start")
    else:
        click.echo("Please fix the issues above before running")


if __name__ == "__main__":
    main()
