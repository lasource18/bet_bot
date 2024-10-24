#!/bin/bash

source ~/Documents/Trading/Betting/Football/Python/bet_bot/.env

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <betting_strategy> <staking_strategy> <bookmaker>"
    exit 1
fi

# Assign arguments to variables
BETTING_STRATEGY=$1
STAKING_STRATEGY=$2
BOOKMAKER=$3

DIR="${LOGS}/match_ratings/errors"

# Check if the directory exists
if [ ! -d "$DIR" ]; then
  # If the directory doesn't exist, create it
  mkdir -p "$DIR"
  echo "Directory $DIR created."
else
  echo "Directory $DIR already exists."
fi

LOG_FILE="${DIR}/$(date '+%Y-%m-%d')_main_errors.log" 

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting script: run_main.sh" >> "$LOG_FILE"

# Run the script with the provided period argument
$PYTHON $MAIN_PYTHON_SCRIPT -B "$BETTING_STRATEGY" -S "$STAKING_STRATEGY" -K "$BOOKMAKER" >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Script executed successfully" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Script failed to execute" >> "$LOG_FILE"
fi

# echo "Main has finished. Logs are saved to $LOG_FILE."
