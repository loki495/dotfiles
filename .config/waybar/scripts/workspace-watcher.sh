#!/bin/sh
# Watches Hyprland's IPC event socket and pokes waybar's custom/ws-* modules
# (SIGRTMIN+8) to refresh instantly on any event that could change which
# workspaces exist or which is focused. Needed because those modules are a
# stand-in for the built-in hyprland/workspaces module, whose click handler
# is broken under Hyprland's new Lua dispatch protocol (see
# workspace-btn.sh). Without this, the buttons would only update on
# waybar's normal polling interval instead of the moment you switch.
#
# Remove this + custom/ws-* + workspace-btn.sh and switch back to
# hyprland/workspaces once waybar ships a fix (Alexays/Waybar#5008).
SOCK="$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket2.sock"

ncat -U "$SOCK" | while IFS= read -r line; do
    case "$line" in
        workspace*|createworkspace*|destroyworkspace*|openwindow*|closewindow*|movewindow*|focusedmon*)
            pkill -RTMIN+8 waybar
            ;;
    esac
done
