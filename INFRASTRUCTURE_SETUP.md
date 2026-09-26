# Infrastructure Setup

This public repository contains only the dotfiles installer and configuration templates.
Real infrastructure configuration (Traefik routes, home-lab topology, credentials) and
files generated for one machine live in a **private `dotfiles-private` repository**, so
your network topology and services stay private.

## Setup After Cloning

After cloning this repo:

```bash
# 1. Clone the private repo next to it (you need access)
git clone git@github.com:<you>/dotfiles-private.git ~/.dotfiles-private

# 2. Link its contents in
~/dotfiles/install.sh private
```

`install.sh private` (see the README's "Private dotfiles" section) symlinks
`ai/CLAUDE.private.md`, everything under `ai/skills/` and `ai/codex-skills/`, and the
units under `systemd/user/` into this checkout and, for `CLAUDE.private.md`, into
`~/.claude/` too. All of those targets are gitignored here. Set `DOTFILES_PRIVATE_ROOT`
if the private repo is not at `~/.dotfiles-private`.

Traefik is separate: `traefik` in this repo is a **tracked symlink** to
`/home/andres/.dotfiles-private/traefik` (the author's path), and `./install.sh traefik`
links `~/www/traefik` to it. On another machine, re-point it first:
`ln -sfn ~/.dotfiles-private/traefik ~/dotfiles/traefik`.

Without the private repo everything else still works: the `private` section skips itself
and the `@CLAUDE.private.md` import in `ai/CLAUDE.md` is ignored silently.

## What's Private

The `dotfiles-private` repo contains:
- `traefik/` — Traefik reverse-proxy configuration (routes, service discovery, TLS)
- `ai/skills/ac495-infrastructure/` and its Codex wrapper — home-lab topology and service inventory
- `ai/CLAUDE.private.md` — the home-network notes (hosts, DNS, Cloudflare tunnel) that `ai/CLAUDE.md` imports
- `systemd/user/` — the systemd units Sessioneer's `host-agent/install.sh` renders for one machine (absolute paths)

Never versioned anywhere: `ai/skills/synced/` (the proprietary skills your claude.ai account syncs).
