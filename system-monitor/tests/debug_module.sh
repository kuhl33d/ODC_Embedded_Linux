#!/bin/bash

echo "=== System Monitor Debug Script ==="

# Check if module is loaded
echo "Module Status:"
lsmod | grep system_monitor

# Check recent kernel messages
echo -e "\nKernel Messages:"
sudo dmesg | tail -n 20

# Check netlink sockets
echo -e "\nNetlink Sockets:"
ss -f netlink

# Check module parameters
echo -e "\nModule Parameters:"
sudo systool -vm system_monitor 2>/dev/null || echo "systool not found (install sysfsutils)"

# Check system load
echo -e "\nSystem Load:"
uptime

# Check memory usage
echo -e "\nMemory Usage:"
free -h

echo -e "\nDebug Complete"
