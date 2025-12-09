# Hotspotchi Changelog

## 2.3.0 (2025-12-08)

- [Feature] Add seasonal character filtering - random/daily_random modes now only select characters available in the current season
- [Feature] Add `get_current_season()` and `is_character_available_now()` helper functions
- [Enhancement] Update character database with correct seasonal characters from Tamagotchi Wiki:
  - Add 11 new v2.1.0 characters (Furawatchi, Chamametchi, Shinshitchi, etc.)
  - Fix Summer characters: Acchitchi (00:0E), Tokonatchi (01:0E), Tropicatchi (02:0E), Yashiharotchi (03:0E)
  - Fix Fall characters: Dekotchi (00:0D), Youngdrotchi (01:0D), Witchi (02:0D), Pumpkitchi (03:0D)
  - Fix Winter characters: Amiamitchi (00:0C), Santaclautchi (01:0C), Akahanatchi (02:0C), Yukipatchi (03:0C)
- [Enhancement] Update character count from 69 to 80 MAC-based characters
- [Docs] Update README with correct character names and counts
- [Maintenance] Add comprehensive tests for seasonal filtering (19 new tests)

## 2.2.9 (2025-12-08)

- [Fix] Fix MAC-based characters not detected by Tamagotchi - now explicitly sets BSSID in hostapd config

## 2.2.8 (2025-12-08)

- [Fix] Fix daily_random mode not changing character at midnight - service now auto-restarts when day changes

## 2.2.7 (2025-12-07)

- [Feature] Add upgrade script (`scripts/upgrade.sh`) for easy updates
- [Docs] Simplify README - remove unnecessary sections, explain daily_random behavior
- [Docs] Update character count to ~90 (69 MAC + 21 special SSIDs)
- [Cleanup] Remove unused environment variable documentation and code comments
- [Maintenance] Add comprehensive tests for CLI, hotspot manager, and web routes (89% total coverage)

## 2.2.6 (2025-12-07)

- [Feature] Add `/api/debug` endpoint with comprehensive troubleshooting info (config, processes, network, services)
- [Feature] Add "Debug Info" link in web UI navbar for easy access to diagnostics
- [Fix] Fix daily random mode always selecting Factory Tama after switching from fixed special SSID mode
- [Fix] Reset ssid_mode to "normal" when switching to rotation modes (daily_random, random, cycle)
- [Fix] Save config to file when mode changes via web UI
- [Fix] Fix save_config to properly serialize Path and Enum types to YAML
- [Maintenance] Add comprehensive test suite for web API routes (60%+ coverage improvement)
- [Maintenance] Add tests for select_combined, exclusion manager, config validation

## 2.2.5 (2025-12-07)

- [Fix] Fix web UI character selection - now restarts via systemd service to avoid process conflicts
- [Fix] Web UI saves config to file before restart so CLI picks up new settings
- [Fix] Only kill hotspotchi-specific dnsmasq processes, not system DNS
- [Fix] Preserve existing config settings (like concurrent_mode) when saving - don't overwrite entire file
- [Fix] Set mac_mode to "fixed" when selecting a character (was only setting character index)
- [Fix] Fix special SSID selection - select_combined() now respects ssid_mode setting
- [Fix] Reset ssid_mode to "normal" when selecting a regular MAC character

## 2.2.4 (2025-12-07)

- [Fix] Fix concurrent mode on 5GHz networks - auto-detect hw_mode (a/g) from channel
- [Fix] Fix virtual interface cleanup - now removes interface regardless of which process created it
- [Fix] Fix hostapd error message capture (outputs to stdout, not stderr)
- [Fix] Systemd services now use venv Python directly for reliability
- [Maintenance] Drop Python 3.9/3.10 support, require Python 3.11+
- [Maintenance] Update README with correct venv pip commands for updating
- [Maintenance] Update install.sh to use venv Python in systemd services

## 2.2.3 (2025-12-07)

- [Fix] Fix web server not loading `web_host` and `web_port` from config file
- [Fix] Sync `__version__` in `__init__.py` with `pyproject.toml`
- [Maintenance] Add comprehensive tests for config loading across all modules (14 new tests)
- [Maintenance] Complete audit of all config usage to ensure consistent loading from `/etc/hotspotchi/config.yaml`

## 2.2.2 (2025-12-07)

- [Fix] Fix CLI `status` command not loading config from file - now respects user config settings
- [Fix] Fix CLI `interactive` command not loading config from file - now preserves concurrent_mode and other settings
- [Fix] Fix CLI `check` command not loading config from file - now shows correct interface and concurrent mode status
- [Refactor] Add `_load_base_config()` and `_config_with_overrides()` helpers to ensure consistent config loading across CLI commands

## 2.2.1 (2025-12-07)

- [Fix] Fix web dashboard not loading config from `/etc/hotspotchi/config.yaml` - this caused concurrent mode settings to be ignored, breaking WiFi when selecting characters via web UI

## 2.2.0 (2025-12-07)

- [Feature] Add special SSID exclusion support to web UI with search, filtering, and toggle controls
- [Feature] Add API endpoints for SSID exclusion management (`/api/ssids/{index}/exclude`, `/api/ssids/{index}/include`, `/api/ssids/{index}/toggle-exclusion`)
- [Feature] Add `GET /api/ssid-exclusions` endpoint to view SSID exclusion summary
- [Feature] Add `DELETE /api/ssid-exclusions` endpoint to clear all SSID exclusions
- [Feature] Add `DELETE /api/all-exclusions` endpoint to clear both character and SSID exclusions
- [Enhancement] Update `/api/ssids` endpoint with `available_only` and `excluded_only` filter parameters
- [Enhancement] Include `excluded` field in SSID API responses
- [Fix] Fix web UI status page showing wrong SSID when special SSID is selected via combined rotation
- [Fix] Fix mypy type errors in cli.py and hotspot.py
- [Maintenance] Update CI workflow to install `[all]` dependencies for complete test coverage
- [Maintenance] Add comprehensive tests for SSID exclusion API endpoints

## 2.1.0 (2025-12-07)

- [Feature] Add special SSIDs to random rotation pool - special SSID characters now appear alongside MAC characters in daily_random, random, and cycle modes
- [Feature] Add `include_special_ssids` config option (default: true) to control special SSID inclusion in rotation
- [Feature] Add SSID exclusion support - exclude specific special SSIDs from rotation
- [Fix] Fix `is_running()` to detect system-wide hostapd processes, not just those started by Hotspotchi

## 2.0.3 (2025-12-07)

- [Feature] Add character exclusion feature - exclude specific characters from random rotation
- [Feature] Add character exclusion UI in web dashboard with toggle buttons and "Include All" reset
- [Enhancement] Add available/excluded character counts in web dashboard
- [Enhancement] Add WiFi interface availability warnings when interface is in use
- [Fix] Fix CLI to properly load config file for `concurrent_mode` setting
- [Docs] Add character exclusions documentation to README

## 2.0.2 (2025-12-07)

- [Feature] Add concurrent mode for running hotspot without losing WiFi station connection
- [Enhancement] Add `concurrent_mode` config option for virtual AP interface creation
- [Enhancement] Add `ap_interface` config option to specify virtual AP interface name

## 2.0.1 (2025-12-07)

- [Fix] Fix default config to use daily random password (null) instead of fixed password
- [Enhancement] Extract characters data to external YAML config file for easier maintenance
- [Docs] Add update instructions to README

## 2.0.0 (2025-12-07)

- [Feature] Initial public release of Hotspotchi
- [Feature] Support for 69 MAC-based Tamagotchi characters
- [Feature] Support for 21 special SSID characters (Sanrio, events, etc.)
- [Feature] Multiple rotation modes: daily_random, random, cycle, fixed, disabled
- [Feature] Web dashboard with DaisyUI interface for monitoring and control
- [Feature] Hotspot control via web interface (start/stop/restart)
- [Feature] Daily rotating WiFi password for security
- [Feature] Raspberry Pi optimized with hostapd + dnsmasq integration
- [Security] Add WPA2 password protection by default
- [Docs] Comprehensive README with security considerations
