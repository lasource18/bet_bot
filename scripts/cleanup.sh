#!/bin/bash

# Check if the correct number of arguments is passed
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 directory extension"
    exit 1
fi

# Assign arguments to variables
TARGET_DIR=$1
FILE_EXT=$2

# Check if the directory exists
if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory $TARGET_DIR does not exist."
    exit 1
fi

# Find and delete all files with the specified extension in the target directory and its subdirectories
find "$TARGET_DIR" -type f -name "*.$FILE_EXT" -exec rm -f {} +

echo "All .$FILE_EXT files in $TARGET_DIR have been deleted."
