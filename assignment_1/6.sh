#!/usr/bin/bash

exception_handler() {
    echo -e "\nkeyboard interrupt caught"
    exit 1
}

trap exception_handler SIGINT

echo "task start"
sleep 10
echo "task end"
