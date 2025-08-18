#!/bin/bash

ROOT_FREE=$(df -BG / | awk 'NR==2 {print $4}')
HOME_FREE=$(df -BG /home | awk 'NR==2 {print $4}')
LABEL="$ROOT_FREE|$HOME_FREE"
CLASS="normal"
# Output JSON for Waybar
echo "{\"text\": \"$LABEL\", \"class\": \"$CLASS\"}"
