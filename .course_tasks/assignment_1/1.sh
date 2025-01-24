#!/usr/bin/bash
read -p "Enter N: " N
sum=0

for ((i=1; i<=N; i++)); 
    do
        sum=$((sum + i))
    done

# arthimatic is better !!!
# sum=$(( (N*(N+1)) / 2 ))

echo "Sum for 1 to $N : $sum"