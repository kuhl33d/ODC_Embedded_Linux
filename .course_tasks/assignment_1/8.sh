#!/bin/bash

if [ $# -ne 1 ]; then
    echo "usage: $0 <directory_path>"
    exit 1
fi

# -d : directory
if [ ! -d "$1" ]; then
    echo "error: Directory $1 not found or not directory"
    exit 1
fi

count=0

# -type f : regular file
# read -r : treats \ as character
# runs in another shell
# find "$1" -type f | while read -r fname; do
#     # < : takes file content
#     if [ $(wc -c < "$fname") -eq 0 ]; then
#         echo "$fname is empty"
#         # count=$((count + 1))
#         ((count++))
#     fi
# done

while read -r fname; do
    if [ $(wc -c < "$fname") -eq 0 ]; then
        echo "$fname is empty"
        ((count++))
    fi
done < <(find "$1" -type f)

# empty_count=$(find "$dir_path" -type f -empty | wc -l)
echo -e "\nFound $count empty files"