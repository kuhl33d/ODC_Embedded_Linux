#!/usr/bin/bash

if [ $# -ne 3 ];
    then
    echo "usage: <n1> <op> <n2>"
    exit 1
fi

res=$(expr $1 $2 $3)

echo $res