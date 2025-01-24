#!/bin/bash

if [ $# -eq 0 ]; then
    echo "usage: $0 number1 number2 number3 ..."
    exit 1
fi

# store array
numbers=($@)
sum=0

# Calculate sum
for num in ${numbers[@]}; do
    # valid number
    if ! [[ "$num" =~ ^[0-9]+$ ]]; then
        echo "error: '$num' is not number"
        exit 1
    fi
    ((sum += num))
done

echo "arr: ${numbers[@]}"
echo "sum: $sum"
echo "count: ${#numbers[@]}"
echo "avg: $((sum/${#numbers[@]}))"