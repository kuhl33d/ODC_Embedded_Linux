#!/bin/bash

if [ $# -ne 2 ]; 
    then
    echo "usage: $0 <input_file> <out_file>"
    exit 1
fi


if [ ! -f $1 ]; 
    then
    echo "error: $1 not found"
    exit 1
fi
if [ ! -r $1 ]; 
    then
    echo "error: $1 not readable"
    exit 1
fi

# empty output file
# -n : supress trailing newline
echo -n "" > $2

i=0
l=1
while IFS= read -r line; do
    # -F : treat string as pattern
    # -x : exact match
    # -q : suppress output
    if ! grep -Fxq "$line" "$2"; 
        then
        if [ $i -ne 0 ];
            then
            echo "" >> "$2"
            fi 
        echo -n $line >> "$2"
        i=$((i+1))
    else
        echo "duplication found $l text: $line"   
    fi
    l=$((l+1))
done < $1

echo "original line count: $(wc -l < $1)"
echo "new line count: $(wc -l < $2)"