#!/usr/bin/env bash
set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

section_header "Linking private dotfiles..."

# The private repo (machine-specific and sensitive files) is cloned next to this
# one. Everything here is optional: without it this section is a no-op, so the
# public installer, and its CI, work on any machine.
PRIVATE_ROOT="${DOTFILES_PRIVATE_ROOT:-$HOME/.dotfiles-private}"

if [ ! -d "$PRIVATE_ROOT" ]; then
  echo_info "No private dotfiles at $PRIVATE_ROOT; skipping."
  exit 0
fi

# Symlink every entry of $1 into directory $2. backup_and_link keeps any real
# file already at a target as <name>.old and leaves a correct link alone.
link_entries () {
  local source_dir="$1" target_dir="$2" entry
  [ -d "$source_dir" ] || return 0
  for entry in "$source_dir"/*; do
    [ -e "$entry" ] || [ -L "$entry" ] || continue
    backup_and_link "$target_dir/$(basename "$entry")" "$entry"
  done
}

link_entries "$PRIVATE_ROOT/ai/skills" "$DOTFILES_ROOT/ai/skills"
link_entries "$PRIVATE_ROOT/ai/codex-skills" "$DOTFILES_ROOT/ai/codex-skills"
# Only makes the unit files visible; systemd itself is the opt-in `systemd` section.
link_entries "$PRIVATE_ROOT/systemd/user" "$DOTFILES_ROOT/.config/systemd/user"

# Imported by ai/CLAUDE.md as @CLAUDE.private.md; a missing file is skipped silently.
if [ -f "$PRIVATE_ROOT/ai/CLAUDE.private.md" ]; then
  backup_and_link "$DOTFILES_ROOT/ai/CLAUDE.private.md" "$PRIVATE_ROOT/ai/CLAUDE.private.md"
fi

echo_success "Private dotfiles linked from $PRIVATE_ROOT."
