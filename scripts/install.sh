#!/bin/bash
#
# Hotspotchi Installation Script for Raspberry Pi
#
# This script installs Hotspotchi and sets up systemd services
# for automatic startup.
#
# Usage: sudo bash install.sh
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installation paths
INSTALL_DIR="/opt/hotspotchi"
CONFIG_DIR="/etc/hotspotchi"
SYSTEMD_DIR="/etc/systemd/system"

# Print colored message
print_msg() {
    local color="$1"
    local msg="$2"
    echo -e "${color}${msg}${NC}"
}

print_step() {
    echo ""
    print_msg "$GREEN" "==> $1"
}

print_error() {
    print_msg "$RED" "ERROR: $1"
}

print_warning() {
    print_msg "$YELLOW" "WARNING: $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Show warning and get confirmation
show_warning() {
    echo ""
    print_msg "$YELLOW" "============================================"
    print_msg "$YELLOW" "  ⚠️  IMPORTANT WARNING"
    print_msg "$YELLOW" "============================================"
    echo ""
    echo "Hotspotchi creates a WiFi hotspot that TAKES OVER your"
    echo "WiFi interface (wlan0). This means:"
    echo ""
    echo "  • Your Pi will DISCONNECT from your home WiFi"
    echo "  • You will LOSE SSH access if connected via WiFi"
    echo "  • The Pi may appear to 'hang' (it's just unreachable)"
    echo ""
    echo "To maintain remote access while running the hotspot:"
    echo "  1. Connect your Pi via Ethernet cable, OR"
    echo "  2. Use a second USB WiFi adapter, OR"
    echo "  3. Enable 'concurrent mode' (if your Pi supports it)"
    echo ""
    read -p "Do you understand and want to continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
}

# Check for concurrent mode support
check_concurrent_support() {
    print_step "Checking concurrent mode support..."

    if ! command -v iw &> /dev/null; then
        apt-get install -y iw > /dev/null 2>&1
    fi

    # Check if chipset supports AP + Station simultaneously
    local support_info
    support_info=$(iw phy phy0 info 2>/dev/null | grep -A 10 'valid interface combinations' || true)

    if echo "$support_info" | grep -qi "ap" && echo "$support_info" | grep -qi "managed"; then
        print_msg "$GREEN" "  ✓ Your WiFi chipset supports concurrent mode!"
        echo "    This means you can run the hotspot while staying"
        echo "    connected to your home WiFi network."
        echo ""
        CONCURRENT_SUPPORTED=true
    else
        print_msg "$YELLOW" "  ✗ Concurrent mode not detected"
        echo "    You'll need Ethernet or a second WiFi adapter"
        echo "    to maintain SSH access while hotspot runs."
        echo ""
        CONCURRENT_SUPPORTED=false
    fi
}

# Ask about concurrent mode
configure_concurrent_mode() {
    if [[ "$CONCURRENT_SUPPORTED" != "true" ]]; then
        return
    fi

    echo ""
    read -p "Enable concurrent mode? (recommended if you don't have Ethernet) (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        ENABLE_CONCURRENT=true
        print_msg "$GREEN" "  Concurrent mode will be enabled"
    else
        ENABLE_CONCURRENT=false
    fi
}

# Check for required commands
check_dependencies() {
    print_step "Checking dependencies..."

    local missing=()

    for cmd in python3 pip3; do
        if ! command -v "$cmd" &> /dev/null; then
            missing+=("$cmd")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        print_error "Missing required commands: ${missing[*]}"
        echo "Install with: sudo apt install python3 python3-pip"
        exit 1
    fi

    echo "  Python3 and pip3 found"
}

# Install system packages
install_system_packages() {
    print_step "Installing system packages..."

    apt-get update -qq
    apt-get install -y hostapd dnsmasq python3-venv

    # Stop and disable default services (we'll manage our own)
    systemctl stop hostapd 2>/dev/null || true
    systemctl stop dnsmasq 2>/dev/null || true
    systemctl disable hostapd 2>/dev/null || true
    systemctl disable dnsmasq 2>/dev/null || true

    echo "  hostapd and dnsmasq installed"
}

# Create directories
create_directories() {
    print_step "Creating directories..."

    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"

    echo "  Created $INSTALL_DIR"
    echo "  Created $CONFIG_DIR"
}

# Install Python package
install_python_package() {
    print_step "Installing Hotspotchi Python package..."

    # Create virtual environment
    python3 -m venv "$INSTALL_DIR/venv"

    # Activate and install
    source "$INSTALL_DIR/venv/bin/activate"
    pip install --upgrade pip

    # Install from current directory or PyPI
    if [[ -f "pyproject.toml" ]]; then
        echo "  Installing from local source..."
        pip install ".[web]"
    else
        echo "  Installing from PyPI..."
        pip install "hotspotchi[web]"
    fi

    deactivate

    echo "  Hotspotchi installed in virtual environment"
}

# Create wrapper scripts
create_wrapper_scripts() {
    print_step "Creating wrapper scripts..."

    # Main CLI wrapper
    cat > /usr/local/bin/hotspotchi << 'EOF'
#!/bin/bash
source /opt/hotspotchi/venv/bin/activate
exec python -m hotspotchi.cli "$@"
EOF
    chmod +x /usr/local/bin/hotspotchi

    # Web server wrapper
    cat > /usr/local/bin/hotspotchi-web << 'EOF'
#!/bin/bash
source /opt/hotspotchi/venv/bin/activate
exec python -m hotspotchi.web.app "$@"
EOF
    chmod +x /usr/local/bin/hotspotchi-web

    echo "  Created /usr/local/bin/hotspotchi"
    echo "  Created /usr/local/bin/hotspotchi-web"
}

# Create default configuration
create_default_config() {
    print_step "Creating default configuration..."

    if [[ ! -f "$CONFIG_DIR/config.yaml" ]]; then
        cat > "$CONFIG_DIR/config.yaml" << EOF
# Hotspotchi Configuration
# See documentation for all options

# WiFi interface (usually wlan0 on Raspberry Pi)
wifi_interface: wlan0

# Concurrent mode: run hotspot while staying connected to home WiFi
# Requires compatible WiFi chipset (Pi 3B+/4/5 typically support this)
concurrent_mode: ${ENABLE_CONCURRENT:-false}

# SSID mode: normal, special, or custom
ssid_mode: normal
default_ssid: Hotspotchi

# MAC mode: daily_random, random, cycle, fixed, or disabled
mac_mode: daily_random

# WiFi password (WPA2)
# null = daily rotating random password (default, recommended)
# "YourPassword" = fixed password (8+ characters)
# "" = open network (not recommended)
wifi_password: null

# Web server settings
web_host: "0.0.0.0"
web_port: 8080
EOF
        echo "  Created $CONFIG_DIR/config.yaml"
    else
        echo "  Config file already exists, skipping"
        # If concurrent mode was selected, update existing config
        if [[ "$ENABLE_CONCURRENT" == "true" ]]; then
            if grep -q "concurrent_mode:" "$CONFIG_DIR/config.yaml"; then
                sed -i 's/concurrent_mode:.*/concurrent_mode: true/' "$CONFIG_DIR/config.yaml"
            else
                echo "concurrent_mode: true" >> "$CONFIG_DIR/config.yaml"
            fi
            echo "  Updated concurrent_mode in existing config"
        fi
    fi
}

# Create systemd service for hotspot
create_hotspot_service() {
    print_step "Creating hotspot systemd service..."

    cat > "$SYSTEMD_DIR/hotspotchi.service" << EOF
[Unit]
Description=Hotspotchi WiFi Hotspot
After=network.target

[Service]
Type=simple
ExecStart=/opt/hotspotchi/venv/bin/python -m hotspotchi.cli start
ExecStop=/bin/kill -SIGTERM \$MAINPID
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    echo "  Created $SYSTEMD_DIR/hotspotchi.service"
}

# Create systemd service for web dashboard
create_web_service() {
    print_step "Creating web dashboard systemd service..."

    cat > "$SYSTEMD_DIR/hotspotchi-web.service" << EOF
[Unit]
Description=Hotspotchi Web Dashboard
After=network.target

[Service]
Type=simple
ExecStart=/opt/hotspotchi/venv/bin/python -m hotspotchi.web.app
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    echo "  Created $SYSTEMD_DIR/hotspotchi-web.service"
}

# Enable and start services
enable_services() {
    print_step "Enabling services..."

    systemctl daemon-reload

    # Enable but don't start hotspot (user should configure first)
    systemctl enable hotspotchi.service
    echo "  Enabled hotspotchi.service (not started - configure first)"

    # Enable and start web dashboard
    systemctl enable hotspotchi-web.service
    systemctl start hotspotchi-web.service
    echo "  Enabled and started hotspotchi-web.service"
}

# Print completion message
print_completion() {
    echo ""
    print_msg "$GREEN" "============================================"
    print_msg "$GREEN" "  Hotspotchi installed successfully!"
    print_msg "$GREEN" "============================================"
    echo ""

    if [[ "$ENABLE_CONCURRENT" == "true" ]]; then
        print_msg "$GREEN" "✓ Concurrent mode ENABLED"
        echo "  Your Pi will stay connected to home WiFi while"
        echo "  running the hotspot. SSH access will be maintained."
        echo ""
    else
        print_msg "$YELLOW" "⚠️  IMPORTANT: Network Access Warning"
        echo "  Starting the hotspot will take over wlan0!"
        echo "  If your Pi is connected via WiFi, you will lose SSH access."
        echo ""
        echo "  Solutions:"
        echo "    • Connect via Ethernet BEFORE starting the hotspot"
        echo "    • Use a second USB WiFi adapter for management"
        echo "    • Re-run installer to enable concurrent mode"
        echo ""
    fi

    echo "Quick Start:"
    echo "  1. Edit configuration: sudo nano $CONFIG_DIR/config.yaml"
    echo "  2. Test manually:      sudo hotspotchi start"
    echo "  3. Start service:      sudo systemctl start hotspotchi"
    echo ""
    echo "Web Dashboard:"
    echo "  Access at: http://$(hostname -I | awk '{print $1}'):8080"
    echo ""
    echo "Useful Commands:"
    echo "  hotspotchi status          - Show current configuration"
    echo "  hotspotchi list-characters - List all characters"
    echo "  hotspotchi list-ssids      - List special SSIDs"
    echo "  hotspotchi interactive     - Interactive menu"
    echo ""
    echo "Service Commands:"
    echo "  sudo systemctl start hotspotchi   - Start hotspot"
    echo "  sudo systemctl stop hotspotchi    - Stop hotspot"
    echo "  sudo systemctl status hotspotchi  - Check status"
    echo "  journalctl -u hotspotchi -f       - View logs"
    echo ""
}

# Main installation
main() {
    echo ""
    print_msg "$GREEN" "============================================"
    print_msg "$GREEN" "  Hotspotchi Installer"
    print_msg "$GREEN" "============================================"

    check_root
    show_warning
    check_dependencies
    check_concurrent_support
    configure_concurrent_mode
    install_system_packages
    create_directories
    install_python_package
    create_wrapper_scripts
    create_default_config
    create_hotspot_service
    create_web_service
    enable_services
    print_completion
}

main "$@"
