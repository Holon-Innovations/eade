#!/bin/bash

min_size=$1
max_size=$2
filename=$3

if [ -z "$min_size" ]
then
  # ask for min size
  read -p "Enter min size: " min_size
fi

if [ -z "$max_size" ]
then
  # ask for max size
  read -p "Enter max size: " max_size
fi

if [ -z "$filename" ]
then
  # ask for the filename, if empty, generate a random one
  read -p "Enter filename (leave empty for random name): " filename
fi

if [ -z "$filename" ] || [ "$filename" == "random" ]
then
    filename=$(uuidgen)
    filename="$filename.bin"
fi

# generate random file
dd if=/dev/urandom of=$filename bs=1 count=$(shuf -i $min_size-$max_size -n 1)

echo "File $filename created with size $(stat -c %s $filename) bytes"