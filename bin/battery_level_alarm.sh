#!/bin/bash

BATPATH=/sys/class/power_supply/BAT1
BAT_FULL=$BATPATH/charge_full
BAT_NOW=$BATPATH/charge_now
bf=$(cat $BAT_FULL)
bn=$(cat $BAT_NOW)
MIN_BATTERY=20
if [ $(( 100 * $bn / $bf )) -lt $MIN_BATTERY ]
then
    notify-send -w -u critical "Low Battery!"
    paplay /usr/share/sounds/freedesktop/stereo/suspend-error.oga
fi
