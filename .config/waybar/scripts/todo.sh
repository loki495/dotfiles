#!/usr/bin/env bash
set -euo pipefail

TODO_FILE="${TODO_FILE:-$HOME/todo}"
MODE="${1:-status}"

# Defaults (override via env if you want)
ICON="${ICON:-📝}"
TRUNCATE_LEN="${TRUNCATE_LEN:-40}"
SHOW_SUMMARY="${SHOW_SUMMARY:-1}"

ensure_file() {
  [[ -f "$TODO_FILE" ]] || touch "$TODO_FILE"
}

escape_json() {
  jq -Rs .
}

status() {
    ensure_file

    mapfile -t lines < "$TODO_FILE"
    total=$(grep -c '^[^ ]' "$TODO_FILE")

    preview=""
    if (( total > 0 )); then
        preview="${lines[0]}"
        text="$ICON $total: $preview"
    else
        text="$ICON 0"
    fi

    # truncate bar text if needed
    if (( ${#text} > TRUNCATE_LEN )); then
        text="${text:0:TRUNCATE_LEN}…"
    fi

    # properly escape both text and tooltip for JSON
    text_json=$(jq -Rn --arg t "$text" '$t')
    tooltip_json=$(jq -Rs . < "$TODO_FILE")

    echo "{\"text\":$text_json,\"tooltip\":$tooltip_json}"
}

edit() {
    TODO_TITLE="Todo"
    yad --text-info --editable --filename="$HOME/todo" --title="$TODO_TITLE" --in-place &
    YAD_PID=$!

    # wait for window to exist
    sleep 0.4

    hyprctl dispatch "movetoworkspace 5,pid:$YAD_PID"
}

add() {
  ensure_file

  new_item=$(zenity \
    --entry \
    --title="Add todo" \
    --text="New todo:")

  [[ -n "${new_item:-}" ]] || exit 0
  printf "%s\n" "$new_item" >> "$TODO_FILE"
}

case "$MODE" in
  status) status ;;
  edit)   edit ;;
  add)    add ;;
  *)
    echo "Unknown mode: $MODE" >&2
    exit 1
    ;;
esac

