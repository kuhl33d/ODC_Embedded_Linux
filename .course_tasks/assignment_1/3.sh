#!/usr/bin/bash

if [ $# -ne 2 ];
    then
    echo "usage: <filename> <word>"
    exit 1
fi

if [ ! -f $1 ];
    then
    echo "file doesn't exist"
    exit 1
fi
if [ ! -r $1 ];
    then
    echo "file not readable"
    exit 1
fi

echo "search for $2 in file $1"
echo "occurrences:"
echo "case sensitive: $(grep -c $2 $1)"
echo "case insensitive: $(grep -ci $2 $1)"