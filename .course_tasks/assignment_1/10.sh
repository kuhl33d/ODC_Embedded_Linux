#!/bin/bash

echo "=== Arithmetic Operations in Shell Script ==="

# Initial values
num1=10
num2=5
echo "Working with numbers: num1=$num1, num2=$num2"

echo -e "\n1. Using let command:"
let sum1=num1+num2
let "product1 = num1 * num2"
let difference1=num1-num2
let "division1 = num1 / num2"
let "power1 = num1 ** 2"
let "modulus1 = num1 % num2"

echo "Sum: $sum1"
echo "Product: $product1"
echo "Difference: $difference1"
echo "Division: $division1"
echo "Power: $power1"
echo "Modulus: $modulus1"

echo -e "\n2. Using double parentheses (( )):"
((sum2 = num1 + num2))
((product2 = num1 * num2))
((difference2 = num1 - num2))
((division2 = num1 / num2))
((power2 = num1 ** 2))
((modulus2 = num1 % num2))

echo "Sum: $sum2"
echo "Product: $product2"
echo "Difference: $difference2"
echo "Division: $division2"
echo "Power: $power2"
echo "Modulus: $modulus2"

echo -e "\n3. Using square brackets $[ ]:"
sum3=$[num1 + num2]
product3=$[num1 * num2]
difference3=$[num1 - num2]
division3=$[num1 / num2]
power3=$[num1 ** 2]
modulus3=$[num1 % num2]

echo "Sum: $sum3"
echo "Product: $product3"
echo "Difference: $difference3"
echo "Division: $division3"
echo "Power: $power3"
echo "Modulus: $modulus3"

echo -e "\n4. Using expr command:"
sum4=$(expr $num1 + $num2)
product4=$(expr $num1 \* $num2)      # Note: * must be escaped
difference4=$(expr $num1 - $num2)
division4=$(expr $num1 / $num2)
modulus4=$(expr $num1 % $num2)       # expr doesn't support power operation

echo "Sum: $sum4"
echo "Product: $product4"
echo "Difference: $difference4"
echo "Division: $division4"
echo "Modulus: $modulus4"

echo -e "\n5. Using arithmetic expansion \$(( )):"
sum5=$((num1 + num2))
product5=$((num1 * num2))
difference5=$((num1 - num2))
division5=$((num1 / num2))
power5=$((num1 ** 2))
modulus5=$((num1 % num2))

echo "Sum: $sum5"
echo "Product: $product5"
echo "Difference: $difference5"
echo "Division: $division5"
echo "Power: $power5"
echo "Modulus: $modulus5"

echo -e "\n6. Increment and Decrement examples:"
count=0

echo "Initial count: $count"

let count+=1
echo "After let count+=1: $count"

((count++))
echo "After ((count++)): $count"

let count=count+1
echo "After let count=count+1: $count"

count=$((count + 1))
echo "After count=\$((count + 1)): $count"

((count--))
echo "After ((count--)): $count"

echo -e "\n7. Complex calculations:"
# Using different methods for complex arithmetic
let "complex1 = (num1 * num2) + (num1 ** 2)"
complex2=$(( (num1 * num2) + (num2 ** 2) ))
complex3=$(expr $num1 \* $num2 + $num1 \* $num1)

echo "Complex calculation 1: $complex1"
echo "Complex calculation 2: $complex2"
echo "Complex calculation 3: $complex3"