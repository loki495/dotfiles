# Dotfiles

[![Test dotfiles install](https://github.com/loki495/dotfiles/actions/workflows/ci.yml/badge.svg)](https://github.com/loki495/dotfiles/actions/workflows/ci.yml)

Personal dotfiles for an Arch/Garuda Linux desktop (Hyprland + waybar) and a set of
PHP/Laravel/OpenCart dev-tooling scripts. Managed as a single repo, symlinked into
place by `install.sh`.

## Installation

### Prerequisites

`git`, `curl`, `wget`, `tar`.

### Steps

1. **Clone the repository:**
   ```bash
   git clone git@github.com:loki495/dotfiles ~/dotfiles
   cd ~/dotfiles
   ```

2. **Run the main installation script:**
   ```bash
   ./install.sh
   ```
   Symlinks the configs below into place (`~/.config/*`, `~/.bashrc`, etc.) and
   prompts for how to install Neovim:
   - **User-local (`--user`):** installs to `$HOME/.local/share/nvim`, symlinked to
     `$HOME/.local/bin/nvim`. Make sure `$HOME/.local/bin` is on `PATH`.
   - **Global (`--global`, needs `sudo`):** installs to `/opt/nvim`, symlinked to
     `/usr/local/bin/nvim`.

   To install/reinstall Neovim on its own later: `./install_neovim.sh --user` or
   `sudo ./install_neovim.sh --global`.

### Post-install

- **Neovim:** plugins install automatically on first run via lazy.nvim.

## Repository structure

### Desktop (`.config/`)

Hyprland + waybar is the live desktop environment; a prior i3/sway/polybar-based
setup has been removed (see "Removed" below).

- `hypr/` — Hyprland compositor config. **Lua-based** (`hyprland.lua` +
  `settings/*.lua`) since Hyprland 0.57 dropped the old hyprlang `.conf` format;
  `settings/` is split by concern (binds, look, rules, autostart, input). `scripts/`
  holds helper scripts invoked from binds/autostart (screenshot, lock, idle,
  dock-toggle, etc.). `hypridle.conf` is a separate daemon (hypridle) that still
  uses its own `.conf` format — unrelated to the compositor's own config format.
- `waybar/` — status bar config + `scripts/` (workspace buttons, brightness,
  network, todo tray, etc.), with separate profiles for the laptop panel (`eDP-1`)
  and TV output (`HDMI-A-1`).
- `fish/` — Fish shell config, aliases, tab-completions, Catppuccin Mocha theme.
- `alacritty/` — terminal emulator config.
- `wireplumber/` — PipeWire/WirePlumber audio routing rules.
- `phpactor/` — PHP language server config (used by both editor configs below).
- `systemd/user/` — user units: clipboard sync, a Unison dev-sync job, the Claude
  Session Manager host agent (socket-activated) + its push-check timer, and a
  `cloudcli` (Claude Code UI) unit.

### Editor

- `nvim/` — Neovim config (Lua), the only editor config in the repo. `lua/andres/`
  is the main tree: `lazy.lua` (plugin manager bootstrap + spec list), `remap.lua`,
  `autocmds.lua`, `functions.lua` (custom user commands), `php_dev.lua` (helpers
  for building/testing a local `php-src` checkout). `after/plugin/*.lua` holds
  per-plugin config (fugitive, harpoon, telescope, treesitter, undotree, oil,
  lsp, etc.).

### Shell & install

- `bash/` — `bashrc`, `dircolors`, and `lib/{common,colors,echos,pushdpopd}` —
  shared helpers sourced by the backup-tools scripts (SSH/MySQL config loading,
  colored output, pushd/popd wrappers).
- `install.sh` / `install_neovim.sh` — top-level dotfiles installer and standalone
  Neovim installer (see Installation above).
- `weekly-cleanup` — cron script: prunes pacman cache, dangling Docker
  images/volumes, old journal logs, `/tmp`.
- `log-notifications.sh` — tails desktop notification bodies via `dbus-monitor`
  (dev/debug tool, not wired into any service).

### `bin/` — personal CLI utilities

Git helpers (`git-rr`, `git-summary`, `rebase-chain`, `git-root-path.php`), PHP
dev-tool wrappers (`phpactor`, `phpcs`, `phpcbf`, `composer`, `phpbrew`), system
utilities (`battery_level_alarm.sh`, `hybrid-sleep`, `pulseaudio-control`,
`reboot-needed-check.sh`, `find-dupes`, `clear-hd-space.php`), an OpenCart
package-mapping tool (`oc`), Claude Code/tmux helpers (`claude-quota`,
`tmux-sessions`, `mcphost`, `boost-query.sh`), a Docker SQL-import helper
(`import-sqlgz-files-docker.sh`), an email notifier (`notify-email`, via curl's
SMTPS support — see backup-tools/README.md), and misc desktop scripts
(`new-reddit-wallpaper`, `dmenu-clear-cache`, `pushbullet-message`, `open-nvim`).

`rg` and `todo-tray` are compiled binaries committed directly to the repo rather
than built from source or installed via package manager — worth revisiting.

### `backup-tools/` — remote-site backup/clone toolkit

Bespoke toolkit for pulling git repos + MySQL dumps from ~44 remote sites into
`~/backups/<site>/`. See `backup-tools/README.md` for the full `backup.conf`
schema and behavior notes (including that `pull` can auto-commit uncommitted
changes on the **remote** site). Highlights: `mysqlbk` (per-table parallel dump),
`full-backup`/`check-backup` (orchestration/status), `clone-site` (clone a site
into a fresh local/remote target), `push`/`pull` (git sync), `check-*` (health
checks: disk space, stale backups, htaccess, etc.), OpenCart packaging
(`oc-package`, `oc-copy`).

### PHP (`php/`)

A small installable PSR-4 package (`loki495/php-lib`, see `composer.json`):
- `src/Core/Config.php` — INI-file config loader.
- `src/Helpers/HDCleaner.php` — used by `bin/clear-hd-space.php` to prune old
  OpenCart error logs, sessions, and DB backup files by age.
- `src/Helpers/helpers.php` — global helpers (`dd()`, `echo_color()`,
  `fix_home_dir()`).

`opencart/dirs-list.txt` / `file-list.txt` — a reference manifest of a stock
OpenCart 1.5.x install's directory/file structure, used by backup-tools scripts
for change detection. Not executable code.

### Claude Code config (`claude/`, `.claude/`)

Gets symlinked into `~/.claude/`. `CLAUDE.md` — global cross-project developer
context (machine layout, git branch model, tooling policy). `RTK.md` — reference
for the `rtk` token-saving CLI proxy hook. `agents/` (code-reviewer, git-helper,
legacy-auditor, test-writer), `commands/` (`cherry-pick-to`, `commits`,
`project-bootstrap`), `hooks/` (Laravel Pint/PHPStan/Rector/Pest automation on
write and pre-commit), `skills/` (git workflow, Laravel/Livewire/Pest/OpenCart/
Rector/DB/frontend conventions). `statusline-command.sh` — custom statusline.
`.claude/settings.local.json` — this repo's own local permission allowlist.
`.mcphost.yml` — config for `mcphost` (local LLM agent host): MCP server
definitions and model params (currently Ollama `gemma:7b`).

### Traefik (`traefik/`)

Symlinked to `~/www/traefik/` (the live reverse-proxy config for the whole
home lab: routes both this machine's Docker-labeled containers and `media`'s
own services — Sonarr, Radarr, etc. — via the file provider, and issues a
wildcard cert for the home domain through Let's Encrypt DNS-01 against
Cloudflare). `docker-compose.yml` runs Traefik itself; `dynamic/` holds the
file-provider routes (`ac495-sites.yml`) and the one legacy self-signed TLS
case (`csm-tls.yml`, for a plain-HTTP-only dev host needing a secure context).
`cloudflared-media-config.yml` is the Cloudflare Tunnel ingress config that
actually runs on `media`. `docker-compose.yml`, `ac495-sites.yml`, and
`cloudflared-media-config.yml` all contain real domain/IP/credential details
for this specific home network, so they're gitignored and populated locally
rather than committed — each has a genericized `*.example` counterpart
checked in for reference.

**`.env` (Cloudflare API token), `acme/` (the real Let's Encrypt account +
wildcard private key), and `certs/` (a self-signed private key) are
gitignored, not tracked** - they exist as real files at the symlinked
location for Traefik to actually run, but must never end up in this repo.

### Other

- `git/` — `.gitconfig` + bash git-completion script.
- `misc/cron/cronlog.php` — PHP wrapper for logging cron job output.
- `misc/docker/setup-dev-container.sh` — provisions a legacy-PHP Apache/Docker
  dev container.
- `misc/systemd/system-sleep/restart-hypridle` — restarts `hypridle` after
  resume (upstream idle-notifier bug workaround); correctly kills any prior
  instance before relaunching.
- `utils/kodi-db/` — Docker-based Kodi media DB puller/updater
  (`pull-and-update.sh`, `update-db.py`).

## Removed

An older i3/sway/polybar/rofi/dunst/picom-based desktop setup (untouched since
2022–mid-2025, fully superseded by the Hyprland+waybar config above) has been
removed from the repo, along with a vendored ~100-file Hyprland "brain" preset
framework whose theme-picker (`brain.sh`) wrote to hyprlang `.conf` files the
Lua-based config no longer reads. The one still-functional script from that
tree (`nwg_dock_toggle.sh`) was kept and moved to `hypr/scripts/`.

`vim/` (plain-Vim config) was also removed: git history showed it 3+ years
stale against `nvim/`'s active maintenance, with real abandoned-migration
debris (a half-finished switch away from ALE left contradictory settings
duplicated across two files). Neovim is now the only editor config here.

## Known rough edges

- `backup-tools`/`mysqlbk` and `clone-site` build remote SSH/mysqldump commands
  via unquoted string concatenation rather than arrays — fragile against
  spaces/metacharacters in config values. Low practical risk today (inputs come
  from trusted local `.conf` files, not untrusted input) but a real fragility if
  ever touched; a full fix means restructuring `run_ssh`/`run_ssh_silent` to take
  array args across every call site.
- `bin/rg` and `bin/todo-tray` are compiled binaries checked into git rather than
  built or installed normally.
