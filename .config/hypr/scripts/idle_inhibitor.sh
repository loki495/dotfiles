#!/bin/bash

a=$(pidof hypridle)
if [[ $a ]]
then
    killall -9 hypridle
    notify-send "idle inhibitor activated"
else
    notify-send "idle inhibitor deactivated"
    # Compute HYPRLAND_INSTANCE_SIGNATURE fresh (most-recently-created
    # instance dir) rather than trusting whatever's inherited in this
    # script's own environment - found live 2026-08-23: this used to just
    # run `hypridle &> /dev/null`, inheriting a stale signature from
    # whatever process last had it cached (e.g. an old shell/waybar
    # instance that predates a later Hyprland restart). A hypridle bound to
    # a dead instance receives no idle-notify events at all, so its
    # listeners - including the 30-minute auto-suspend one - silently never
    # fire again until the next restart: no error, no crash, just a
    # permanent no-op that looks like "the laptop just doesn't suspend
    # anymore". Same lookup as the sleep-hook that already does this
    # correctly (misc/systemd/system-sleep/restart-hypridle). Also missing
    # backgrounding before (a bare `hypridle &> /dev/null` with no trailing
    # `&` blocks this whole script in the foreground) - setsid detaches it
    # into its own session regardless of what invoked this script.
    HYPRLAND_INSTANCE_SIGNATURE="$(ls -t "${XDG_RUNTIME_DIR:-/run/user/1000}/hypr" 2>/dev/null | head -1)" \
        setsid hypridle &> /dev/null &
fi
