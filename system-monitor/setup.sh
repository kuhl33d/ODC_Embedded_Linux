#!/bin/bash

# setup.sh - System Monitor Setup Script with Install/Uninstall options

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directories
PROJECT_ROOT=$(pwd)
KERNEL_MODULE_DIR="$PROJECT_ROOT/kernel_module"
DAEMON_DIR="$PROJECT_ROOT/daemon"
UI_DIR="$PROJECT_ROOT/ui"
WEB_UI_DIR="$UI_DIR/web"
TUI_DIR="$UI_DIR/tui"

# Log file
LOG_FILE="$PROJECT_ROOT/setup.log"

# Function to log messages
log_message() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $1" >> "$LOG_FILE"
}

# Output functions
print_status() {
    echo -e "${BLUE}[*]${NC} $1"
    log_message "$1"
}

print_success() {
    echo -e "${GREEN}[+]${NC} $1"
    log_message "[SUCCESS] $1"
}

print_error() {
    echo -e "${RED}[-]${NC} $1"
    log_message "[ERROR] $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
    log_message "[WARNING] $1"
}

# Function to confirm action
confirm_action() {
    local prompt="$1"
    local default="$2"
    
    while true; do
        read -p "$prompt [y/n] ($default): " response
        response=${response:-$default}
        case $response in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

# Function to uninstall everything
uninstall() {
    print_status "Starting uninstallation process..."

    # Stop and disable services
    print_status "Stopping services..."
    systemctl stop system-monitor-web system-monitor-daemon system-monitor 2>/dev/null
    systemctl disable system-monitor-web system-monitor-daemon system-monitor 2>/dev/null

    # Remove service files
    print_status "Removing service files..."
    rm -f /etc/systemd/system/system-monitor*.service
    systemctl daemon-reload

    # Unload kernel module
    print_status "Unloading kernel module..."
    rmmod system_monitor 2>/dev/null

    # Remove virtual environment
    if [ -d "$PROJECT_ROOT/venv" ]; then
        print_status "Removing virtual environment..."
        rm -rf "$PROJECT_ROOT/venv"
    fi

    # Clean kernel module
    if [ -d "$KERNEL_MODULE_DIR" ]; then
        print_status "Cleaning kernel module..."
        cd "$KERNEL_MODULE_DIR"
        make clean
        cd "$PROJECT_ROOT"
    fi

    # Remove control script
    if [ -f "$PROJECT_ROOT/monitor-control.sh" ]; then
        print_status "Removing control script..."
        rm -f "$PROJECT_ROOT/monitor-control.sh"
    fi

    print_success "Uninstallation completed successfully!"
}

# Function to check system requirements
check_requirements() {
    print_status "Checking system requirements..."
    
    # Check for root privileges
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root"
        exit 1
    fi

    local required_packages=(
        "build-essential"
        "linux-headers-$(uname -r)"
        "python3"
        "python3-pip"
        "python3-venv"
        "git"
    )

    local missing_packages=()
    for package in "${required_packages[@]}"; do
        if ! dpkg -l | grep -q "^ii  $package"; then
            missing_packages+=("$package")
        fi
    done

    if [ ${#missing_packages[@]} -ne 0 ]; then
        print_warning "The following packages are required and will be installed:"
        printf '%s\n' "${missing_packages[@]}"
        if confirm_action "Do you want to install these packages?" "y"; then
            apt-get update
            apt-get install -y "${missing_packages[@]}"
        else
            print_error "Cannot proceed without required packages"
            exit 1
        fi
    fi
}

# Installation steps
install_kernel_module() {
    if confirm_action "Install kernel module?" "y"; then
        print_status "Building and installing kernel module..."
        cd "$KERNEL_MODULE_DIR"
        make clean && make
        insmod system_monitor.ko
        cd "$PROJECT_ROOT"
        
        if confirm_action "Create systemd service for kernel module?" "y"; then
            cat > /etc/systemd/system/system-monitor.service << EOL
[Unit]
Description=System Monitor Kernel Module
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/sbin/insmod $KERNEL_MODULE_DIR/system_monitor.ko
ExecStop=/sbin/rmmod system_monitor

[Install]
WantedBy=multi-user.target
EOL
            systemctl daemon-reload
            systemctl enable system-monitor
            systemctl start system-monitor
        fi
    fi
}

install_python_env() {
    if confirm_action "Set up Python virtual environment?" "y"; then
        print_status "Setting up Python virtual environment..."
        python3 -m venv "$PROJECT_ROOT/venv"
        source "$PROJECT_ROOT/venv/bin/activate"
        pip install -r "$DAEMON_DIR/requirements.txt"
        pip install -r "$TUI_DIR/requirements.txt"
    fi
}

install_daemon() {
    if confirm_action "Install daemon service?" "y"; then
        print_status "Setting up daemon service..."
        cat > /etc/systemd/system/system-monitor-daemon.service << EOL
[Unit]
Description=System Monitor Daemon
After=network.target system-monitor.service

[Service]
Type=simple
User=$SUDO_USER
ExecStart=$PROJECT_ROOT/venv/bin/python3 $DAEMON_DIR/monitor_daemon.py
WorkingDirectory=$DAEMON_DIR
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOL
        systemctl daemon-reload
        systemctl enable system-monitor-daemon
        systemctl start system-monitor-daemon
    fi
}

install_web_server() {
    if confirm_action "Install web interface service?" "y"; then
        print_status "Setting up web server..."
        cat > /etc/systemd/system/system-monitor-web.service << EOL
[Unit]
Description=System Monitor Web Interface
After=network.target system-monitor-daemon.service

[Service]
Type=simple
User=$SUDO_USER
ExecStart=/usr/bin/python3 -m http.server 8080
WorkingDirectory=$WEB_UI_DIR
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOL
        systemctl daemon-reload
        systemctl enable system-monitor-web
        systemctl start system-monitor-web
    fi
}

create_control_script() {
    if confirm_action "Create control script?" "y"; then
        print_status "Creating control script..."
        cat > "$PROJECT_ROOT/monitor-control.sh" << 'EOL'
#!/bin/bash

case "$1" in
    "start")
        sudo systemctl start system-monitor system-monitor-daemon system-monitor-web
        ;;
    "stop")
        sudo systemctl stop system-monitor-web system-monitor-daemon system-monitor
        ;;
    "restart")
        sudo systemctl restart system-monitor system-monitor-daemon system-monitor-web
        ;;
    "status")
        echo "Kernel Module Status:"
        sudo systemctl status system-monitor
        echo -e "\nDaemon Status:"
        sudo systemctl status system-monitor-daemon
        echo -e "\nWeb Server Status:"
        sudo systemctl status system-monitor-web
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
EOL
        chmod +x "$PROJECT_ROOT/monitor-control.sh"
    fi
}

# Main installation function
install() {
    print_status "Starting installation process..."
    
    check_requirements
    install_kernel_module
    install_python_env
    install_daemon
    install_web_server
    create_control_script

    print_success "Installation completed!"
    echo -e "\nAvailable commands:"
    echo "1. './monitor-control.sh start|stop|restart|status' - Control services"
    echo "2. Access web interface at http://localhost:8080"
    echo "3. Run TUI: source venv/bin/activate && python3 $TUI_DIR/monitor_tui.py"
}

# Main script
main() {
    # Clear or create log file
    > "$LOG_FILE"

    echo -e "${BLUE}System Monitor Setup${NC}"
    echo "1. Install"
    echo "2. Uninstall"
    echo "3. Exit"
    
    read -p "Select an option (1-3): " choice
    
    case $choice in
        1)
            install
            ;;
        2)
            if confirm_action "Are you sure you want to uninstall?" "n"; then
                uninstall
            fi
            ;;
        3)
            echo "Exiting..."
            exit 0
            ;;
        *)
            print_error "Invalid option"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"