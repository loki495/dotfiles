#!/usr/bin/env sh

## Add this to your wm startup file.

# Terminate already running bar instances
killall -q polybar #nm-applet battery_monitor_loop

#get hidePoly PID and kill it
#kill -9 `ps aux | grep hidePoly | grep -v grep | awk '{ print $2; }'`

# Wait until the processes have been shut down
while pgrep -u $UID -x polybar >/dev/null; do sleep 1; done

# feh --bg-fill /home/andres/.config/polybar/wallpaper/budgie.jpg

while pgrep -x polybar >/dev/null; do
    sleep 1;
done

polybar main -c ~/.config/polybar/config.ini &
# polybar bottom -c ~/.config/polybar/config.ini &

sleep 1

#nm-applet &

#battery_monitor_loop &

#xev not triggering when window is hidden, so not bothering for now
#hidePoly.sh -p 3 -d top -H
