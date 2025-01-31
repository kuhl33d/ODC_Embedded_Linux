# Real-Time System Monitor
```
system-monitor/
├── README.md
├── daemon/
│   ├── README.md
│   ├── install.sh
│   ├── monitor_daemon.py
│   ├── requirements.txt
│   ├── system-monitor.service
│   └── uninstall.sh
├── kernel_module/
│   ├── Makefile
│   ├── README.md
│   ├── module_control.sh
│   └── system_monitor.c
├── setup.sh
├── tests/
│   ├── build.sh
│   ├── debug_module.sh
│   ├── test_client.py
│   ├── test_netlink
│   └── test_netlink.c
└── ui/
    ├── tui/
    │   ├── README.md
    │   ├── monitor_tui.log
    │   ├── monitor_tui.py
    │   └── monitor_tui.v2.py
    └── web/
        ├── README.md
        ├── index.html
        ├── server.py
        └── static/
            ├── css/
            │   └── style.css
            └── js/
                └── monitor.js

9 directories, 26 files
```
A comprehensive system monitoring solution with kernel-level metrics collection, featuring both Terminal UI and Web UI interfaces. This project demonstrates real-time system metrics collection and visualization using Linux kernel modules, WebSocket communication, and modern UI frameworks.

## Features

- Kernel-level system metrics collection
- Real-time data updates using Netlink and WebSocket
- Terminal-based UI (similar to htop)
- Web-based UI (similar to Windows Task Manager)
- Process monitoring
- CPU usage graphs
- Memory usage visualization
- Network statistics

## Architecture

### Components

1. **Kernel Module**
   - Collects system metrics at kernel level
   - Uses Netlink for real-time communication
   - Monitors CPU, memory, and process information

2. **Daemon Service**
   - Bridges kernel space and user space
   - Converts binary data to JSON format
   - Provides WebSocket server for UI clients

3. **User Interfaces**
   - Terminal UI (TUI)
   - Web Interface
   - Real-time updates via WebSocket

### Data Flow

Kernel Module → Netlink → Daemon → WebSocket → UI Clients (TUI/Web)


## Prerequisites

- Linux kernel headers
- Python 3.8+
- gcc and make
- Node.js (for web development)

## Installation

1. Install system dependencies:
```bash
sudo apt update
sudo apt install build-essential linux-headers-$(uname -r) python3-dev python3-pip
```

2. Clone the repository:
```bash
git clone https://github.com/kuhl33d/ODC_Embedded_Linux.git
cd ODC_Embedded_Linux/system-monitor
```

3.Build and install the kernel module:
```bash
cd kernel_module
make
sudo insmod system_monitor.ko
```

4. Install Python dependencies:
```bash
cd ../daemon
pip install -r requirements.txt
```

## Usage

1. Start the daemon service:
```bash
python3 daemon/monitor_daemon.py
```

2. For Terminal UI:
```bash
python3 ui/tui/monitor_tui.py
```

3. For Web UI:
```bash
cd ui/web
python3 -m http.server 8080
```

Then open `http://localhost:8080` in your browser.

## Technical Details

### **Kernel Module**
- Uses Netlink sockets for user space communication
- Implements timer-based metrics collection
- Provides real-time system statistics

### **Daemon Service**
- Asynchronous processing using asyncio
- WebSocket server for real-time client updates
- Binary data parsing and JSON conversion

### **User Interfaces**
- TUI: Built with Python curses
- Web UI: HTML5, CSS3, JavaScript
- Real-time updates using WebSocket

## Configuartion

The system can be configured through various parameters:

1. Kernel Module:

    - Collection interval (default: 1 second)
    - Maximum processes tracked (default: 100)

2. Daemon:

    - WebSocket port (default: 8765)
    - Logging level

3. UI:

    - Update interval
    - Display preferences

## Development

### **Building the Kernel Module**
```bash
cd kernel_module
make clean
make
```

### **Contributing**
1. Fork the repo
2. Create your feature branch
3. Commit your changes 
4. Push to the branch
5. Create a Pull Request

## Troubleshooting
Common issues and solutions:

1. Kernel module fails to load:
    - Check kernel version compatibility
    - Verify kernel headers are installed
    - Check system logs: `dmesg | tail`

2. WebSocket connection fails:
    - Verify daemon is running
    - Check port availability
    - Check firewall settings

## License
This project is licensed under the GPL License - see the LICENSE file for details.

## Acknowledgments
- Linux Kernel Documentation
- Python asyncio community
- Various open-source monitoring tools
- Authors

## Authors
- Khaled Abdel-Nasser @kuhl33d

## Version History

- 0.1.0
    - Intial Release
    - Basic functionality implementation