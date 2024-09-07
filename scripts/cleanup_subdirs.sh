#!/bin/bash

# Check if the correct number of arguments is passed
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 directory"
    exit 1
fi

# Assign the argument to a variable
TARGET_DIR=$1

# Check if the directory exists
if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory $TARGET_DIR does not exist."
    exit 1
fi

# Find and delete all subdirectories and their contents within the target directory
find "$TARGET_DIR" -mindepth 1 -type d -exec rm -rf {} +

echo "All subdirectories in $TARGET_DIR have been deleted."
