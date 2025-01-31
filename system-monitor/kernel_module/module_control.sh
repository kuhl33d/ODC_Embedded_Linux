#!/bin/bash
# module_control.sh

MODULE_NAME="system_monitor"
MODULE_PATH="./kernel_module/system_monitor.ko"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if module is loaded
is_module_loaded() {
    lsmod | grep "^$MODULE_NAME" >/dev/null
    return $?
}

# Function to build module
build_module() {
    echo -e "${YELLOW}Building kernel module...${NC}"
    cd kernel_module
    make clean && make
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Module built successfully${NC}"
        cd ..
        return 0
    else
        echo -e "${RED}Failed to build module${NC}"
        cd ..
        return 1
    fi
}

# Function to load module
load_module() {
    if is_module_loaded; then
        echo -e "${YELLOW}Module is already loaded${NC}"
        return 0
    fi

    echo -e "${YELLOW}Loading kernel module...${NC}"
    sudo insmod $MODULE_PATH
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Module loaded successfully${NC}"
        echo -e "Check kernel messages with: ${YELLOW}dmesg | tail${NC}"
        return 0
    else
        echo -e "${RED}Failed to load module${NC}"
        return 1
    fi
}

# Function to unload module
unload_module() {
    if ! is_module_loaded; then
        echo -e "${YELLOW}Module is not loaded${NC}"
        return 0
    fi

    echo -e "${YELLOW}Unloading kernel module...${NC}"
    sudo rmmod $MODULE_NAME
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Module unloaded successfully${NC}"
        return 0
    else
        echo -e "${RED}Failed to unload module${NC}"
        return 1
    fi
}

# Function to show module status
show_status() {
    echo -e "${YELLOW}Module Status:${NC}"
    if is_module_loaded; then
        echo -e "${GREEN}Module is loaded${NC}"
        echo -e "\nModule details:"
        modinfo $MODULE_PATH
        echo -e "\nKernel messages:"
        dmesg | grep $MODULE_NAME | tail
    else
        echo -e "${RED}Module is not loaded${NC}"
    fi
}

# Main script logic
case "$1" in
    "build")
        build_module
        ;;
    "load")
        load_module
        ;;
    "unload")
        unload_module
        ;;
    "reload")
        unload_module && load_module
        ;;
    "status")
        show_status
        ;;
    *)
        echo "Usage: $0 {build|load|unload|reload|status}"
        echo "  build  - Build the kernel module"
        echo "  load   - Load the kernel module"
        echo "  unload - Unload the kernel module"
        echo "  reload - Unload and load the module"
        echo "  status - Show module status"
        exit 1
        ;;
esac

exit 0