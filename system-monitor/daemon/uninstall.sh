#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root${NC}"
    exit 1
fi

echo -e "${YELLOW}Uninstalling System Monitor...${NC}"

# Stop and disable service
systemctl stop system-monitor
systemctl disable system-monitor

# Remove files
rm -f /usr/local/bin/system_monitor_daemon.py
rm -f /etc/systemd/system/system-monitor.service

# Unload kernel module
rmmod system_monitor

# Remove logs
rm -f /var/log/system_monitor.log
rm -f /var/log/system_monitor.error.log

# Reload systemd
systemctl daemon-reload

echo -e "${GREEN}Uninstallation complete!${NC}"