#!/bin/bash

source ~/Documents/Trading/Betting/Football/Python/bet_bot/.env

# Check if the correct number of arguments is passed
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <directory> <crawler>"
    exit 1
fi

# Assign arguments to variables
CRAWLER_DIR=$1
CRAWLER_NAME=$2

LOG_FILE="${HIST_DATA_LOG_PATH}/$(date '+%Y-%m-%d')_historical_data.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting script: run_crawler.sh" >> "$LOG_FILE"

# Check if the directory exists
if [ ! -d "$CRAWLER_DIR" ]; then
    echo "Error: Directory $CRAWLER_DIR does not exist."
    exit 1
fi

# Change to the crawler directory
cd "$CRAWLER_DIR" || exit

# Run the scrapy crawler and redirect output to the log file
$SCRAPY crawl $CRAWLER_NAME >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Script executed successfully" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Script failed to execute" >> "$LOG_FILE"
fi

# echo "Crawler has finished. Logs are saved to $LOG_FILE."
