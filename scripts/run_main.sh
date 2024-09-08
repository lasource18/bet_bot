#!/bin/bash

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 betting_strategy staking_strategy bookmaker"
    exit 1
fi

# Assign arguments to variables
BETTING_STRATEGY=$1
STAKING_STRATEGY=$2
BOOKMAKER=$3
LOG_FILE="/Users/claude-micaelguinan/Documents/Trading/Betting/Football/Python/bet_bot/logs/match_ratings/errors/$(date '+%Y-%m-%d')_main_errors.log" 

# Path to the Python script
PYTHON="/Users/claude-micaelguinan/Documents/Trading/Betting/Football/Python/bet_bot/venv/bin/python"
PYTHON_SCRIPT="/Users/claude-micaelguinan/Documents/Trading/Betting/Football/Python/bet_bot/main.py"

# Run the script with the provided period argument
$PYTHON $PYTHON_SCRIPT -B "$BETTING_STRATEGY" -S "$BETTING_STRATEGY" -K "$BOOKMAKER" &> "$LOG_FILE"

echo "Main has finished. Logs are saved to $LOG_FILE."
