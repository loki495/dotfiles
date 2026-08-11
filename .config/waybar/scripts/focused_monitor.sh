#!/bin/sh
mon=$(hyprctl monitors -j | jq -r '.[] | select(.focused==true) | .name')
if [ "$mon" = "HDMI-A-1" ]; then
    echo '{"text":"📺 TV focus","class":"tv"}'
else
    echo '{"text":"💻 Laptop focus","class":"laptop"}'
fi
