#!/bin/bash
# Toggles the laptop's own screen (eDP-1) off/on via brightness only --
# deliberately NOT `hyprctl dispatch dpms`, which triggers a hardware-cursor
# corruption / compositor-hang bug on this hybrid Intel/NVIDIA setup (see the
# comment on the cursor block in settings/manual_settings.conf).
#
# Uses its own save file rather than brightnessctl's built-in -s/-r, since
# hypridle's idle-dim listener also uses brightnessctl -s/-r and shares the
# same save slot -- colliding with it caused brightness to get stuck at a
# stale low value in the past.

STATE_FILE="$HOME/.cache/laptop_screen_toggle_brightness"
MAX=$(brightnessctl max)
CURRENT=$(brightnessctl get)
THRESHOLD=$(( MAX * 2 / 100 ))

if [ "$CURRENT" -le "$THRESHOLD" ] && [ -f "$STATE_FILE" ]; then
    SAVED=$(cat "$STATE_FILE")
    brightnessctl set "$SAVED" >/dev/null
    notify-send "Laptop screen on"
else
    echo "$CURRENT" > "$STATE_FILE"
    brightnessctl set 1 >/dev/null
    notify-send "Laptop screen off"
fi
