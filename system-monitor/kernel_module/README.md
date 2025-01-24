# Kernel Module

1. Collects CPU, memory, and process statistics
2. Uses Netlink for communication
3. Updates metrics every second
4. Handles memory safely with proper locking
5. Provides detailed process information

## Key features:
- Real-time metrics collection
- Safe memory handling
- Process tracking
- CPU per-core statistics
- Detailed memory information


## Basic commands for kernel module management:

```bash
# Build the module
cd kernel_module
make clean && make

# Load the module
sudo insmod system_monitor.ko

# Check if module is loaded
lsmod | grep system_monitor

# View kernel messages (useful for debugging)
dmesg | tail

# Unload the module
sudo rmmod system_monitor

# View module information
modinfo system_monitor.ko
```

## For automatic loading at boot time:
```bash
# Create a module configuration file
sudo nano /etc/modules-load.d/system_monitor.conf
# Add the following line:
system_monitor

# Copy the module to the kernel modules directory
sudo cp kernel_module/system_monitor.ko /lib/modules/$(uname -r)/extra/
sudo depmod -a
```

## For Debugging:

```bash
# View kernel messages in real-time
sudo dmesg -w

# Check system logs
sudo journalctl -f

# View module parameters (if any)
systool -vm system_monitor

# Check module dependencies
modprobe --show-depends system_monitor
```

## Common troubleshooting
```bash
# If module fails to load, check kernel logs
dmesg | tail

# Check if module is blacklisted
cat /etc/modprobe.d/* | grep system_monitor

# Verify module signature (if secure boot is enabled)
mokutil --sb-state

# Force unload module (use with caution)
sudo rmmod -f system_monitor

# List module dependencies
lsmod | grep system_monitor
```

## Create a systemd service for automatic module loading:
```INI
# /etc/systemd/system/system-monitor.service
[Unit]
Description=System Monitor Kernel Module
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/sbin/modprobe system_monitor
ExecStop=/sbin/rmmod system_monitor

[Install]
WantedBy=multi-user.target
```

### **Enable the service:**
```bash 
sudo systemctl enable system-monitor
sudo systemctl start system-monitor
```