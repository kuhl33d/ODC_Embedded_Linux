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

echo -e "${YELLOW}Installing System Monitor...${NC}"

# Create directories
mkdir -p /usr/local/lib/system_monitor
mkdir -p /var/log/system_monitor

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip3 install websockets typing-extensions

# Copy files
echo -e "${YELLOW}Copying files...${NC}"
cp daemon/monitor_daemon.py /usr/local/bin/system_monitor_daemon.py
chmod +x /usr/local/bin/system_monitor_daemon.py

# Install kernel module
echo -e "${YELLOW}Installing kernel module...${NC}"
cd kernel_module
make clean
make
insmod system_monitor.ko
cd ..

# Install systemd service
echo -e "${YELLOW}Installing systemd service...${NC}"
cp system-monitor.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable system-monitor
systemctl start system-monitor

# Create log files
touch /var/log/system_monitor.log
touch /var/log/system_monitor.error.log
chmod 644 /var/log/system_monitor.*

echo -e "${GREEN}Installation complete!${NC}"
echo -e "\nTo check status:"
echo "systemctl status system-monitor"
echo -e "\nTo view logs:"
echo "journalctl -u system-monitor -f"