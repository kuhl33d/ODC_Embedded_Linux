#!/bin/bash

if [ $# -ne 1 ]; 
    then
    echo "usage: $0 <directory_path>"
    exit 1
fi

# -d : directory
if [ ! -d "$1" ]; 
    then
    echo "error: Directory $1 not found or not directory"
    exit 1
fi

# -type f : regular file
# read -r : treats \ as character
home=$(pwd)
cd $1
while read -r fname; do
    lower=$(echo "$fname" | tr [:upper:] [:lower:])
    if [ $fname != $lower ];
    then
        echo "renaming $fname to $lower"
        mv "$fname" "$lower"
    else
        echo "$fname already lowercase"
    fi
done < <(find ./ -type f)
cd "$home"