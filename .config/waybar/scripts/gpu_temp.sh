#!/bin/bash

# Extract temperature value only (e.g., "64C" → "64")
TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits)

# Set label
LABEL="GPU: ${TEMP}°C"

# Determine class based on temperature
if [ "$TEMP" -lt 60 ]; then
  CLASS="cool"
elif [ "$TEMP" -lt 75 ]; then
  CLASS="warm"
elif [ "$TEMP" -lt 90 ]; then
  CLASS="hot"
else
  CLASS="critical"
fi

# Output JSON for Waybar
echo "{\"text\": \"$LABEL\", \"class\": \"$CLASS\"}"
