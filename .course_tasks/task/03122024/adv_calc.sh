#!/bin/bash

stop=0

while [ $stop -eq 0 ]; do
    read -p "n1: " n1
    read -p "operation: " op
    read -p "n2: " n2

    case $op in
        +)
            res=$((n1 + n2))
            ;;
        -)
            res=$((n1 - n2))
            ;;
        \*)
            res=$((n1 * n2))
            ;;
        /)
            if [ n2 -eq 0 ];
            then
                echo "division by 0"
                exit 1
            done
            res=$((n1 / n2))
            ;;
        *)
            echo "Invalid operation"
            continue
            ;;
    esac
    
    echo "$n1 $op $n2 = $res"

    read -p "again y/n? " choice

    if [ $choice != 'y' ]; then
        echo "exiting..."
        stop=1
    fi
done