#!/bin/sh
# One clickable waybar workspace button. Exists because waybar's built-in
# hyprland/workspaces module's click handler is broken under Hyprland's new
# Lua dispatch protocol (compiled into waybar, not fixable via config --
# see Alexays/Waybar#5008), so this replaces it with N separate
# custom/ws-<N> modules driven by this script. Remove this + custom/ws-* +
# workspace-watcher.sh and switch back to hyprland/workspaces once waybar
# ships a fix.
#
# Usage: workspace-btn.sh <workspace_id> <output_name>
WS="$1"
OUTPUT="$2"

WORKSPACES_JSON="$(hyprctl workspaces -j)"
ACTIVE_ID="$(hyprctl monitors -j | jq -r --arg output "$OUTPUT" '.[] | select(.name == $output) | .activeWorkspace.id')"

EXISTS="$(printf '%s' "$WORKSPACES_JSON" | jq -e --argjson ws "$WS" 'any(.id == $ws)' >/dev/null 2>&1 && echo yes)"

if [ "$WS" != "$ACTIVE_ID" ] && [ "$EXISTS" != "yes" ]; then
    # Hide: no windows on this workspace and it's not the active one.
    # Empty text is waybar's convention for a hidden/collapsed module.
    printf '{"text":""}\n'
    exit 0
fi

if [ "$WS" = "$ACTIVE_ID" ]; then
    printf '{"text":"%s","class":"active"}\n' "$WS"
else
    printf '{"text":"%s","class":""}\n' "$WS"
fi
