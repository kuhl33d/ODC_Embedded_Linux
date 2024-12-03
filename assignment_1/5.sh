#!/usr/bin/bash

fact() {
    # Correct input validation
    if [[ ! $1 =~ ^[0-9]+$ ]]; then
        echo "Error: Please enter a valid non-negative integer"
        return 1
    fi

    # Base case
    if [ "$1" -eq 0 ] || [ "$1" -eq 1 ]; then
        echo 1
        return 0
    fi
    x=$1
    n=$((x - 1))

    expr $x \* $(fact $n)
}


if [ $# -eq 0 ]; then
    echo "usage: $0 <number>"
    exit 1
fi

fact "$1"