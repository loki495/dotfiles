#!/usr/bin/env bash
# Automates the manual tmux-based verification used throughout the 2026-09-01/02
# nvim-treesitter debugging session: for each filetype nvim/lua/andres/autocmds.lua
# wires up via vim.treesitter.start(), open a real fixture in a detached tmux
# session, move the cursor (not just open-and-capture - that's what actually
# caught the original treesitter-context crash), then assert real per-token
# syntax highlighting happened and no error popup appeared.
#
# GOTCHA (if you ever manually simulate a missing parser to test this script):
# Neovim's parser lookup globs `parser/<lang>.*`, so renaming a .so in place
# (e.g. `rust.so` -> `rust.so.bak`) does NOT actually hide it - the glob still
# matches the .bak suffix and nvim happily loads it. You must move the file
# fully out of the parser directory (e.g. to /tmp) for a real negative test.
# Also: vim.treesitter.get_parser()/.start() return nil/false on failure
# rather than throwing, so a bare `pcall(...)` around them always reports
# ok=true regardless of whether a parser was actually found - check the
# returned value (or vim.treesitter.highlighter.active[buf]), not just pcall's
# own ok flag. Both confirmed empirically - see RESULT.md.
#
# PREREQUISITE: this script does NOT install parsers/queries itself - it expects
# `install_neovim.sh --parsers` and `--queries` (or `~/.local/share/nvim/site/
# {parser,queries}/`) to already be populated, and expects `~/.config/nvim` to
# already resolve to this repo's nvim/ directory (e.g. via install.sh's
# 60-neovim.sh section, or already symlinked as on a normal dev machine) so a
# plain `nvim <file>` picks up this repo's config. See RESULT.md for why: nvim's
# `-u <path>` flag overrides which init file loads but NOT which directory is on
# 'runtimepath', so `-u <repo>/nvim/init.lua` alone would fail to find the
# require("andres.*") modules unless ~/.config/nvim already IS that repo.
#
# Usage: scripts/ci/test-nvim-highlighting.sh [filetype ...]
#        (default: all filetypes in FT_LANG below)

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FIXTURES_DIR="$REPO_ROOT/scripts/ci/fixtures"

# filetype -> tree-sitter language (mirrors the ft_to_lang exceptions in
# nvim/lua/andres/autocmds.lua: sh->bash, typescriptreact->tsx, else identical)
declare -A FT_LANG=(
    [sh]=bash
    [html]=html
    [yaml]=yaml
    [javascript]=javascript
    [typescript]=typescript
    [typescriptreact]=tsx
    [vue]=vue
    [json]=json
    [php]=php
    [rust]=rust
    [toml]=toml
)

declare -A FT_FIXTURE=(
    [sh]=test.sh
    [html]=test.html
    [yaml]=test.yaml
    [javascript]=test.js
    [typescript]=test.ts
    [typescriptreact]=test.tsx
    [vue]=test.vue
    [json]=test.json
    [php]=test.php
    [rust]=test.rs
    [toml]=test.toml
)

# Real, blocking/crash error markers ONLY - deliberately NOT bare "Error" or
# bare "traceback". Both legitimately appear in the benign, non-blocking
# nvim-lspconfig deprecation notice (tailwind-tools triggers
# `vim.deprecate(..., backtrace=true)` once per nvim process, which prints its
# own "stack traceback:" section as part of the *expected* notice). Verified
# empirically against a live capture - see RESULT.md.
ERROR_MARKERS=(
    "Press ENTER or type command to continue"
    "E117:"
    "E5108:"
    "Error in "
    "Error executing"
)

# Minimum distinct truecolor foreground codes (38;2;r;g;b) required across a
# buffer capture to count as "real per-token highlighting happened" rather
# than a flat/default color. 2 could just be gutter-vs-content even with
# broken highlighting; 3+ means at least two distinct token colors besides
# the gutter. See RESULT.md for the empirical basis for this threshold.
MIN_DISTINCT_COLORS=3

pass_count=0
fail_count=0

test_one() {
    local ft="$1"
    local lang="${FT_LANG[$ft]:-}"
    local fixture_name="${FT_FIXTURE[$ft]:-}"

    if [ -z "$lang" ] || [ -z "$fixture_name" ]; then
        echo "FAIL $ft: unknown filetype (not in FT_LANG/FT_FIXTURE)"
        return 1
    fi

    local fixture="$FIXTURES_DIR/$fixture_name"
    if [ ! -f "$fixture" ]; then
        echo "FAIL $ft: fixture not found: $fixture"
        return 1
    fi

    local session="tshl_$$_${ft}"
    tmux kill-session -t "$session" >/dev/null 2>&1
    tmux new-session -d -s "$session" -x 220 -y 50
    tmux send-keys -t "$session" -- "nvim '$fixture'" Enter
    sleep 2

    # Pass 1: raw capture right after opening, before dismissing anything.
    # This is what proves a real error (or the benign deprecation notice)
    # would/wouldn't trip our markers at the point they'd actually appear.
    local raw marker
    raw=$(tmux capture-pane -t "$session" -p)
    for marker in "${ERROR_MARKERS[@]}"; do
        if grep -qF "$marker" <<<"$raw"; then
            echo "FAIL $ft: error marker found on open: $marker"
            tmux kill-session -t "$session" >/dev/null 2>&1
            return 1
        fi
    done

    # Dismiss any startup notification, then move the cursor around - this is
    # what actually reproduced the original treesitter-context crash; opening
    # a file alone did not reliably trigger it.
    tmux send-keys -t "$session" Enter
    sleep 0.3
    tmux send-keys -t "$session" Enter
    sleep 0.3
    tmux send-keys -t "$session" -- "Gggjjjkkjj"
    sleep 1

    local raw2
    raw2=$(tmux capture-pane -t "$session" -p)
    for marker in "${ERROR_MARKERS[@]}"; do
        if grep -qF "$marker" <<<"$raw2"; then
            echo "FAIL $ft: error marker found after cursor movement: $marker"
            tmux kill-session -t "$session" >/dev/null 2>&1
            return 1
        fi
    done

    # Ground-truth check: ask nvim itself whether the TREESITTER highlighter
    # (not Neovim's legacy regex :syntax fallback, which can independently
    # produce several distinct colors of its own - confirmed empirically by
    # temporarily removing a parser and seeing the color check alone still
    # pass) is actually attached to this buffer.
    tmux send-keys -t "$session" Escape
    sleep 0.2
    tmux send-keys -t "$session" -- ":lua print('TSACTIVE=' .. tostring(vim.treesitter.highlighter.active[vim.api.nvim_get_current_buf()] ~= nil))" Enter
    sleep 0.5
    local ts_check
    ts_check=$(tmux capture-pane -t "$session" -p)

    # Color check: capture WITH escape codes and count distinct truecolor
    # foreground sequences actually rendered. Kept as a second, independent
    # signal (catches "attached but somehow not rendering") alongside the
    # ground-truth check above, which is what actually distinguishes
    # treesitter highlighting from the legacy regex fallback.
    local colored distinct_colors
    colored=$(tmux capture-pane -t "$session" -p -e)
    distinct_colors=$(grep -oE '38;2;[0-9]+;[0-9]+;[0-9]+' <<<"$colored" | sort -u | wc -l)

    tmux kill-session -t "$session" >/dev/null 2>&1

    if ! grep -qF "TSACTIVE=true" <<<"$ts_check"; then
        echo "FAIL $ft: vim.treesitter.highlighter is NOT active for this buffer (lang=$lang)"
        local parser_path="$HOME/.local/share/nvim/site/parser/${lang}.so"
        local query_path="$HOME/.local/share/nvim/site/queries/${lang}"
        [ -f "$parser_path" ] || echo "     hint: parser missing: $parser_path"
        [ -d "$query_path" ] || echo "     hint: query dir missing: $query_path"
        return 1
    fi

    if [ "$distinct_colors" -lt "$MIN_DISTINCT_COLORS" ]; then
        local parser_path="$HOME/.local/share/nvim/site/parser/${lang}.so"
        local query_path="$HOME/.local/share/nvim/site/queries/${lang}"
        echo "FAIL $ft: only $distinct_colors distinct highlight color(s) (need >= $MIN_DISTINCT_COLORS)"
        [ -f "$parser_path" ] || echo "     hint: parser missing: $parser_path"
        [ -d "$query_path" ] || echo "     hint: query dir missing: $query_path"
        return 1
    fi

    echo "PASS $ft: $distinct_colors distinct highlight colors, no error markers"
    return 0
}

filetypes=("$@")
if [ ${#filetypes[@]} -eq 0 ]; then
    mapfile -t filetypes < <(printf '%s\n' "${!FT_LANG[@]}" | sort)
fi

for ft in "${filetypes[@]}"; do
    if test_one "$ft"; then
        pass_count=$((pass_count + 1))
    else
        fail_count=$((fail_count + 1))
    fi
done

echo ""
echo "nvim highlighting check: $pass_count passed, $fail_count failed"
[ "$fail_count" -eq 0 ]
