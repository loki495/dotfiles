#!/bin/bash

current=$(brightnessctl g)
max=$(brightnessctl m)
percent=$(( current * 100 / max ))

# Generate menu of brightness levels (10–100%)
choice=$(seq 10 10 100 | wofi --dmenu --prompt "Brightness (now ${percent}%)")

# If user selected something, apply it
if [[ -n "$choice" ]]; then
    brightnessctl set "${choice}%"
fi
