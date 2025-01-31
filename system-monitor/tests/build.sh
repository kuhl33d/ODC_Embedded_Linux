#!/bin/bash

# Build C test client
gcc -o test_netlink test_netlink.c

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "Test utilities built successfully"
    echo "Usage:"
    echo "  ./test_netlink     - Run C test client"
    echo "  python3 test_client.py - Run Python test client"
else
    echo "Error building test utilities"
    exit 1
fi
