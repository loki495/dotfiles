#!/usr/bin/env bash
# Merges TOML fragments into a Codex config.toml as one managed block, leaving everything
# else in the file alone (Codex rewrites its own config: trust levels, hook hashes, UI state).
# Usage: codex-merge-config.sh <config.toml> <fragment.toml>...
# Rerunnable: the block between the markers is replaced, and a same-named table that sits
# outside it (a hand-made one) is dropped first so TOML never sees a duplicate table.
set -euo pipefail

config="$1"; shift
BEGIN="# BEGIN dotfiles-managed (do not edit; see ai/codex/ in the dotfiles repo)"
END="# END dotfiles-managed"

block=$(mktemp); names=$(mktemp); out=$(mktemp)
trap 'rm -f "$block" "$names" "$out"' EXIT

{ echo "$BEGIN"; for f in "$@"; do [ -f "$f" ] && { cat "$f"; echo; }; done; echo "$END"; } > "$block"
sed -n 's/^\[\([^]]*\)\].*/\1/p' "$block" > "$names"

[ -f "$config" ] || : > "$config"
awk -v begin="$BEGIN" -v end="$END" -v namesfile="$names" '
  BEGIN { while ((getline n < namesfile) > 0) want[n] = 1 }
  $0 == begin { inblock = 1; next }
  inblock { if ($0 == end) inblock = 0; next }
  /^\[/ {
    h = $0; sub(/^\[/, "", h); sub(/\].*$/, "", h); drop = 0
    for (n in want) if (h == n || index(h, n ".") == 1) drop = 1
  }
  !drop { print }
' "$config" | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}' > "$out"
[ -s "$out" ] && echo >> "$out"
cat "$block" >> "$out"

if cmp -s "$out" "$config"; then exit 0; fi
cp -p "$config" "$config.dotfiles-bak" 2>/dev/null || true
cat "$out" > "$config"
