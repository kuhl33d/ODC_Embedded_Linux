#!/usr/bin/bash
if [ $# -ne 2 ];
    then
    echo "usage: <n1> <n2>"
    exit 1
fi

if [ $1 -eq $2 ];
    then
    echo "$1 equal $2"
elif [ $1 -lt $2 ];
    then
    echo "$1 less than $2"
elif [ $1 -gt $2 ];
    then
    echo "$1 greater than $2"
fi