#!/usr/bin/bash

if [ $# -ne 1 ]; then
    echo "usage: <command_file>"
    exit 1
fi

if [ ! -f "$1" ]; then
    echo "file doesn't exist"
    exit 1
fi

> out.txt
> error.txt

while read -r line; do
    if [ -z "$line" ]; then
        continue
    fi
    
    read -r cmd args <<< "$line"
    
    
    if [ "$cmd" = "cat" ] && [ -z "$args" ]; then
        echo "'cat' without arguments is not allowed" >> error.txt
        echo "'cat' without arguments is not allowed"
        continue
    fi
    
    output=$(timeout 5s bash -c "$line" 2>>error.txt)
    code=$?
    
    if [ $code -eq 0 ]; then
        echo -e "$line ::\n$output" >> out.txt
        echo -e "$line ::\n$output"
    elif [ $code -eq 124 ]; then
        echo "$line timed out" >> error.txt
    else
        echo "$line command not found"
    fi
done < "$1"