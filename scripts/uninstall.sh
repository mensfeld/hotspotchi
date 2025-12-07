#!/bin/bash
#
# HotSpotchi Uninstallation Script
#
# This script removes HotSpotchi and all associated files.
#
# Usage: sudo bash uninstall.sh
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

print_msg() {
    local color="$1"
    local msg="$2"
    echo -e "${color}${msg}${NC}"
}

print_step() {
    echo ""
    print_msg "$GREEN" "==> $1"
}

print_warning() {
    print_msg "$YELLOW" "WARNING: $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_msg "$RED" "ERROR: This script must be run as root (use sudo)"
        exit 1
    fi
}

# Stop services
stop_services() {
    print_step "Stopping services..."

    systemctl stop hotspotchi.service 2>/dev/null || true
    systemctl stop hotspotchi-web.service 2>/dev/null || true

    echo "  Services stopped"
}

# Disable services
disable_services() {
    print_step "Disabling services..."

    systemctl disable hotspotchi.service 2>/dev/null || true
    systemctl disable hotspotchi-web.service 2>/dev/null || true

    echo "  Services disabled"
}

# Remove systemd service files
remove_service_files() {
    print_step "Removing systemd service files..."

    rm -f "$SYSTEMD_DIR/hotspotchi.service"
    rm -f "$SYSTEMD_DIR/hotspotchi-web.service"

    systemctl daemon-reload

    echo "  Service files removed"
}

# Remove wrapper scripts
remove_wrapper_scripts() {
    print_step "Removing wrapper scripts..."

    rm -f /usr/local/bin/hotspotchi
    rm -f /usr/local/bin/hotspotchi-web

    echo "  Wrapper scripts removed"
}

# Remove installation directory
remove_install_dir() {
    print_step "Removing installation directory..."

    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        echo "  Removed $INSTALL_DIR"
    else
        echo "  $INSTALL_DIR not found, skipping"
    fi
}

# Handle configuration
handle_config() {
    print_step "Handling configuration..."

    if [[ -d "$CONFIG_DIR" ]]; then
        echo "  Configuration directory: $CONFIG_DIR"
        read -p "  Remove configuration files? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$CONFIG_DIR"
            echo "  Configuration removed"
        else
            echo "  Configuration preserved"
        fi
    else
        echo "  No configuration directory found"
    fi
}

# Restore WiFi
restore_wifi() {
    print_step "Restoring WiFi..."

    # Kill any running hostapd/dnsmasq that we started
    killall hostapd 2>/dev/null || true
    killall dnsmasq 2>/dev/null || true

    # Restart NetworkManager
    systemctl restart NetworkManager 2>/dev/null || true

    echo "  WiFi restored to normal mode"
}

# Print completion message
print_completion() {
    echo ""
    print_msg "$GREEN" "============================================"
    print_msg "$GREEN" "  HotSpotchi uninstalled successfully!"
    print_msg "$GREEN" "============================================"
    echo ""
    echo "Note: hostapd and dnsmasq packages were NOT removed."
    echo "To remove them: sudo apt remove hostapd dnsmasq"
    echo ""
}

# Main uninstallation
main() {
    echo ""
    print_msg "$GREEN" "============================================"
    print_msg "$GREEN" "  HotSpotchi Uninstaller"
    print_msg "$GREEN" "============================================"

    check_root

    read -p "Are you sure you want to uninstall HotSpotchi? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Uninstallation cancelled."
        exit 0
    fi

    stop_services
    disable_services
    remove_service_files
    remove_wrapper_scripts
    remove_install_dir
    handle_config
    restore_wifi
    print_completion
}

main "$@"
