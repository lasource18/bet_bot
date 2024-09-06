#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 betting_strategy period"
    exit 1
fi

# Assign arguments to variables
BETTING_STRATEGY=$1
PERIOD=$2

# Path to the Python script
PYTHON="/Users/claude-micaelguinan/Documents/Trading/Betting/Football/Python/bet_bot/venv/bin/python"
PYTHON_SCRIPT="/Users/claude-micaelguinan/Documents/Trading/Betting/Football/Python/bet_bot/reports_generator.py"

# Run the script with the provided period argument
$PYTHON $PYTHON_SCRIPT -B "$BETTING_STRATEGY" -P "$PERIOD"
