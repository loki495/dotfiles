#!/bin/bash
status=$(hyprctl activewindow | grep -oP 'flags:\s*\K.*')

# Simplify status to key flags
if echo "$status" | grep -q "RESIZING"; then
  echo "Resizing"
elif echo "$status" | grep -q "MOVING"; then
  echo "Moving"
elif echo "$status" | grep -q "FULLSCREEN"; then
  echo "Fullscreen"
else
  echo ""
fi
