#!/bin/bash

# Check if the correct number of arguments is passed
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 directory crawler log_file"
    exit 1
fi

# Assign arguments to variables
CRAWLER_DIR=$1
CRAWLER_NAME=$2
LOG_FILE=$3

# Check if the directory exists
if [ ! -d "$CRAWLER_DIR" ]; then
    echo "Error: Directory $CRAWLER_DIR does not exist."
    exit 1
fi

# Change to the crawler directory
cd "$CRAWLER_DIR" || exit

# Run the scrapy crawler and redirect output to the log file
scrapy crawl $CRAWLER_NAME &> "$LOG_FILE"

echo "Crawler has finished. Logs are saved to $LOG_FILE."
