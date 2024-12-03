#!/usr/bin/bash
if [ $# -ne 1 ];
    then
    echo "usage: <n1>"
    exit 1
fi
if [ $1 -lt 0 ];
    then
    echo "invalid number"
    exit
fi

x=0

while [ $x -lt $1 ]; 
    do
    echo -n "$x "
    ((x++))
done
echo ""