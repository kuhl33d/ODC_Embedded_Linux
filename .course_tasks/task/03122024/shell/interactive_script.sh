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
    output=$(eval "$line" 2>>error.txt)

    if [ $? -eq 0 ]; then
        echo -e "$line ::\n$output" >> out.txt
        # echo "$line" | bash 
        $line 
    else
        echo "$line command not found"
    fi
done < "$1"