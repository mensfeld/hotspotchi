# HotSpotchi

[![CI](https://github.com/mensfeld/hotspotchi/actions/workflows/ci.yml/badge.svg)](https://github.com/mensfeld/hotspotchi/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Create WiFi access points with custom MAC addresses and SSIDs for meeting characters in Tamagotchi Uni's **Tama Search** feature.

## Why HotSpotchi?

The Tamagotchi Uni's **Tama Search** feature lets you meet special characters by detecting nearby WiFi networks. The character you encounter depends on the last two bytes of the WiFi access point's MAC address, or in some cases, specific SSIDs for event-exclusive characters.

The problem? You'd need to physically visit different locations with different WiFi networks to collect all characters - or wait for special real-world events that may never happen in your area.

**HotSpotchi solves this** by turning your Raspberry Pi into a WiFi hotspot that can spoof any MAC address or SSID, letting you:

- Meet all 69+ characters from home without traveling
- Access event-exclusive characters (like Sanrio collaborations) that require specific SSIDs
- Automatically rotate through characters daily, or cycle through the entire collection
- Track which characters you've encountered via the web dashboard

Perfect for completionists, rural players without access to many WiFi networks, or anyone who just wants to meet their favorite Tamagotchi characters without leaving the house.

## Features

- **69 MAC-based characters** - Meet different Tamagotchi characters by changing the WiFi MAC address (includes seasonal characters)
- **21 special SSID characters** - Access event-exclusive characters with special network names
- **Multiple rotation modes**:
  - `daily_random` - Different character each day (from all 69), same all day (default)
  - `random` - New random character each boot
  - `cycle` - Progress through all characters in order
  - `fixed` - Always show a specific character
  - `disabled` - Use device default MAC
- **Web dashboard** - Monitor and control via browser with DaisyUI interface
- **Raspberry Pi optimized** - Works with hostapd + dnsmasq

## Quick Start

### Installation (Raspberry Pi)

```bash
# Clone the repository
git clone https://github.com/mensfeld/hotspotchi.git
cd hotspotchi

# Run the installer
sudo bash scripts/install.sh
```

### Manual Installation

```bash
# Install system dependencies
sudo apt install hostapd dnsmasq python3-pip python3-venv

# Install HotSpotchi
pip install hotspotchi

# Or with web dashboard
pip install "hotspotchi[web]"
```

## Security Considerations

**HotSpotchi requires root/sudo privileges** to manage network interfaces, MAC addresses, and system services. Before running, please be aware:

- **Review the code** - This software modifies network settings. Always review code from any source before running with elevated privileges.
- **Dedicated device recommended** - Use a dedicated Raspberry Pi for HotSpotchi rather than a device with sensitive data.
- **Network isolation** - The hotspot created is a separate network. Consider your network topology and who can connect.
- **No warranty** - This software is provided "as is" without warranty. Use at your own risk.
- **Web dashboard access** - If running the web interface, it binds to `0.0.0.0` by default (accessible from your network). Restrict access if needed or bind to `127.0.0.1` for local-only access.

### WiFi Network Security

The HotSpotchi hotspot is **secured by default with WPA2** to prevent unwanted connections:

- **Daily rotating password** - By default, a random 16-character alphanumeric password is generated each day. The password changes at midnight, similar to how daily character selection works.
- **No connection required** - Tamagotchi Uni only needs to *detect* the network name (SSID), not actually connect to it. The password exists solely to prevent random devices from joining your hotspot.
- **Password options in config**:
  - `wifi_password: null` - Daily rotating random password (default, recommended)
  - `wifi_password: "YourPassword"` - Use a fixed password of your choice
  - `wifi_password: ""` - Open network with no password (not recommended)

```yaml
# /etc/hotspotchi/config.yaml
# Default: null (generates random daily password)
wifi_password: null
```

If you're uncomfortable running third-party code as root, you can:
1. Review all source code in `src/hotspotchi/`
2. Run in a virtual machine or container first
3. Use a freshly imaged SD card dedicated to this purpose

## Usage

### Command Line

```bash
# Start hotspot with daily random character
sudo hotspotchi start

# Start with specific character (fixed mode)
sudo hotspotchi start --mac-mode fixed --character-index 5

# Start with special SSID character
sudo hotspotchi start --ssid-mode special --special-index 0

# Interactive menu
sudo hotspotchi interactive

# List all characters
hotspotchi list-characters

# List special SSIDs
hotspotchi list-ssids

# Check system status
hotspotchi status

# Verify dependencies
hotspotchi check
```

### Web Dashboard

Start the web server:

```bash
# Start web dashboard
hotspotchi-web

# Or with custom port
hotspotchi-web --port 8080
```

Access at `http://raspberrypi.local:8080` (or your Pi's IP address).

The dashboard shows:
- Current SSID and MAC address
- Active character name
- Countdown to next character (daily mode)
- Upcoming characters (cycle mode)
- Searchable character browser
- Special SSID selector

### As a Service

```bash
# Start hotspot service
sudo systemctl start hotspotchi

# Start web dashboard service
sudo systemctl start hotspotchi-web

# Enable at boot
sudo systemctl enable hotspotchi hotspotchi-web

# Check status
sudo systemctl status hotspotchi

# View logs
journalctl -u hotspotchi -f
```

## Configuration

Edit `/etc/hotspotchi/config.yaml`:

```yaml
# WiFi interface (usually wlan0 on Raspberry Pi)
wifi_interface: wlan0

# SSID mode: normal, special, or custom
ssid_mode: normal
default_ssid: HotSpotchi

# MAC mode: daily_random, random, cycle, fixed, or disabled
mac_mode: daily_random

# For fixed mode - character index (0 = Mametchi)
fixed_character_index: 0

# For special mode - SSID index (0 = Angel & Devil)
special_ssid_index: 0

# WPA2 password (default: null = daily rotating random password)
# Tamagotchi only needs to detect the network, not connect
# Options: null (daily random), "YourPassword" (fixed), "" (open - not recommended)
wifi_password: null

# Web server settings
web_host: "0.0.0.0"
web_port: 8080
```

### Environment Variables

All settings can be overridden with `HOTSPOTCHI_` prefix:

```bash
export HOTSPOTCHI_MAC_MODE=daily_random
export HOTSPOTCHI_SSID_MODE=normal
export HOTSPOTCHI_WIFI_INTERFACE=wlan0
```

## How It Works

### With Tamagotchi Uni

1. Start the HotSpotchi hotspot on your Raspberry Pi
2. On your Tamagotchi Uni, go to **Tama Search**
3. Select the network when it appears
4. Meet the character determined by the current MAC/SSID!

### MAC-Based Characters

Characters are determined by the last two bytes of the MAC address. HotSpotchi uses the format:

```
02:7A:6D:A0:XX:YY
```

Where:
- `02` = Locally administered unicast address
- `7A:6D:A0` = "TAMA" signature
- `XX:YY` = Character identifier

### Special SSIDs

Some characters are triggered by specific WiFi network names (SSIDs) that were originally only available at special events in Japan. HotSpotchi includes 21 known special SSIDs:

- **Angel & Devil** - World Tamagotchi Tour
- **Makiko** - Bandai Cross stores
- **1123 Mametchi** - 28th Anniversary event
- And more! Run `hotspotchi list-ssids` for the full list.

## Character Reference

### MAC Characters (80+)

| Index | Character | MAC Ending |
|-------|-----------|------------|
| 0 | Mametchi | 00:00 |
| 1 | Weeptchi | 00:10 |
| 2 | Hypertchi | 00:20 |
| ... | ... | ... |

Run `hotspotchi list-characters` for the complete list.

### Seasonal Characters

Set your Tamagotchi's date to meet seasonal characters:

| Season | Months | Characters |
|--------|--------|------------|
| Spring | Mar-May | Rosetchi, Yotsubatchi, Hanafuwatchi, Musiharutchi |
| Summer | Jun-Aug | Soyofuwatchi, Hyurutchi, Kiramotchi, Awawatchi |
| Fall | Sep-Nov | Momijitchi, Chestnut Angel, Ginkgotchi, Kinokotchi |
| Winter | Dec-Feb | Yukinkotchi, Snowboytchi, Fuyukotchi, Yuki Onna |

## Development

```bash
# Clone and install in development mode
git clone https://github.com/mensfeld/hotspotchi.git
cd hotspotchi
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=hotspotchi --cov-report=term-missing

# Run linter
ruff check src/ tests/

# Run formatter
ruff format src/ tests/

# Type checking
mypy src/hotspotchi
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Run linter (`ruff check .`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Adding New Characters

If you discover new character byte combinations or SSIDs:

1. Add entries to `src/hotspotchi/characters.py`
2. Add tests in `tests/test_characters.py`
3. Submit a pull request with source/verification info

## Troubleshooting

### WiFi not appearing

```bash
# Check if hostapd is running
sudo systemctl status hotspotchi

# Check for errors
journalctl -u hotspotchi -n 50

# Verify interface
ip link show wlan0

# Unblock WiFi if blocked
sudo rfkill unblock wifi
```

### Same character every day

Make sure you're using `daily_random` mode:

```bash
sudo hotspotchi start --mac-mode daily_random
```

### Permission denied

HotSpotchi requires root privileges for network configuration:

```bash
sudo hotspotchi start
```

## Updating

To update HotSpotchi to the latest version:

```bash
# Navigate to your HotSpotchi directory
cd /path/to/hotspotchi

# Stop the running services
sudo systemctl stop hotspotchi hotspotchi-web

# Pull the latest changes
git pull origin master

# Reinstall the package
pip install -e ".[web]" --upgrade

# Restart services
sudo systemctl start hotspotchi hotspotchi-web
```

If you installed via the install script, you can also re-run it:

```bash
sudo bash scripts/install.sh
```

To check for available updates without applying them:

```bash
cd /path/to/hotspotchi
git fetch origin
git log HEAD..origin/master --oneline
```

## Uninstallation

```bash
sudo bash scripts/uninstall.sh
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Tamagotchi community for discovering MAC/SSID mappings
- [Tamagotchi Wiki](https://tamagotchi.fandom.com/) for character information
- Everyone who shared special event SSIDs

## Disclaimer

This project is not affiliated with or endorsed by Bandai. Tamagotchi is a registered trademark of Bandai.
