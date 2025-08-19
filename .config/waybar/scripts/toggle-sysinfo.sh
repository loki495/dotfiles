#!/bin/bash

# Check if sysbar is running
if pgrep -f "python-popup.py" > /dev/null; then
    pkill -f "python-popup.py"
else
    ~/.config/waybar/scripts/python-popup.py
fi

