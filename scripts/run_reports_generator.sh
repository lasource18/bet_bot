#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <betting_strategy>"
    exit 1
fi

# Assign arguments to variables
BETTING_STRATEGY=$1
LOG_FILE="/Users/claude-micaelguinan/Documents/Trading/Betting/Football/Python/bet_bot/logs/match_ratings/errors/$(date '+%Y-%m-%d')_reports_generator_errors.log" 

# Path to the Python script
PYTHON="/Users/claude-micaelguinan/Documents/Trading/Betting/Football/Python/bet_bot/venv/bin/python"
PYTHON_SCRIPT="/Users/claude-micaelguinan/Documents/Trading/Betting/Football/Python/bet_bot/reports_generator.py"

# Run the script with the provided period argument
$PYTHON $PYTHON_SCRIPT -B "$BETTING_STRATEGY" &> "$LOG_FILE"

echo "Reports generator has finished. Logs are saved to $LOG_FILE."
