#!/bin/bash
# Hotspotchi Upgrade Script
# Upgrades Hotspotchi to the latest version

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Hotspotchi Upgrade Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Please run as root (sudo bash scripts/upgrade.sh)${NC}"
    exit 1
fi

# Determine the Hotspotchi directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOTSPOTCHI_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${YELLOW}Upgrading Hotspotchi in: ${HOTSPOTCHI_DIR}${NC}"
echo

# Stop services
echo -e "${YELLOW}Stopping services...${NC}"
systemctl stop hotspotchi hotspotchi-web 2>/dev/null || true

# Pull latest changes
echo -e "${YELLOW}Pulling latest changes...${NC}"
cd "$HOTSPOTCHI_DIR"
git pull origin master

# Reinstall package
echo -e "${YELLOW}Installing updated package...${NC}"
/opt/hotspotchi/venv/bin/pip install -e ".[all]" --upgrade --quiet

# Restart services
echo -e "${YELLOW}Restarting services...${NC}"
systemctl start hotspotchi hotspotchi-web

echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Upgrade complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo -e "Services restarted. Check status with:"
echo -e "  ${YELLOW}sudo systemctl status hotspotchi hotspotchi-web${NC}"
