#!/bin/bash

source $BET_BOT_ENV_FILE

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <betting_strategy>"
    exit 1
fi

# Assign arguments to variables
BETTING_STRATEGY=$1

DIR="${LOGS}/match_ratings/errors"

# Check if the directory exists
if [ ! -d "$DIR" ]; then
  # If the directory doesn't exist, create it
  mkdir -p "$DIR"
  echo "Directory $DIR created."
else
  echo "Directory $DIR already exists."
fi

LOG_FILE="${DIR}/$(date '+%Y-%m-%d')_bet_settler_errors.log" 

# Run the script with the provided period argument
$PYTHON $BET_SETTLER_PYTHON_SCRIPT -B "$BETTING_STRATEGY" &> "$LOG_FILE"

echo "Bet settler has finished. Logs are saved to $LOG_FILE."
