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
   The path matters — `bash/bashrc` and several configs reference
   `~/dotfiles/...` unconditionally, so a clone anywhere else leaves those
   pointing at nothing.

2. **Run the installer:**
   ```bash
   ./install.sh              # run every section
   ./install.sh --list       # list available sections
   ./install.sh bash git     # run only the named sections
   ```

`install.sh` is a thin entrypoint: it checks the commands it needs, then sources
each numbered section in `scripts/install/` in order. Each section is also a
standalone script (`./scripts/install/10-bash.sh`), so re-running just the one
you touched is the normal way to work here.

| Section | Links / does |
| --- | --- |
| `bash` | `~/.bashrc`, `~/.dircolors` |
| `git` | `~/.gitconfig` |
| `desktop-config` | `~/bin`, and `~/.config/{hypr,waybar,fish,wireplumber}` |
| `systemd` | `~/.config/systemd`, then `systemctl --user daemon-reload` |
| `ai-tools` | `~/AGENTS.md` and `~/.claude/*`; also opencode, Codex and Antigravity config, each skipped unless that tool is on `PATH` |
| `neovim` | `~/.config/nvim`, then installs Neovim itself (below) |
| `traefik` | `~/www/traefik` |

Most sections move an existing target aside to `<target>.old` before linking
(`backup_and_link` in `scripts/install/lib.sh`) and are safe to re-run. Two do
not: `desktop-config` and the `~/.claude/` links in `ai-tools` remove their
targets outright, so a real directory sitting at one of those paths is lost
rather than backed up.

The `neovim` section prompts for how to install Neovim itself:

- **User-local:** installs to `$HOME/.local/share/nvim`, symlinked to
  `$HOME/.local/bin/nvim`. Make sure `$HOME/.local/bin` is on `PATH`.
- **Global (needs `sudo`):** installs to `/opt/nvim`, symlinked to
  `/usr/local/bin/nvim`.

Set `NVIM_INSTALL_CHOICE=1` (user-local) or `2` (global) to answer that prompt
non-interactively. To install or reinstall Neovim on its own later:
`./install_neovim.sh --user` or `sudo ./install_neovim.sh --global`.

### Post-install

- **Neovim:** plugins install automatically on first run via lazy.nvim.
- **Claude Code:** `ai/settings.json` hardcodes this machine's home directory in
  its hook paths; under a different username those need editing after linking.
  The installer prints a reminder.

## Tests

```bash
export PATH="$PWD/scripts/ci/stubs:$PATH"
DOTFILES_CI_TEST=1 scripts/ci/test-install.sh
```

Runs the real `install.sh` against `$HOME`, so it requires the explicit
`DOTFILES_CI_TEST=1` opt-in and is meant for a throwaway container, not your own
machine. The stubs on `PATH` stand in for `systemctl` and `sudo`, which a
container has no working equivalent of.

`.github/workflows/ci.yml` runs exactly this on every push, in an
`archlinux:latest` container. See "Install & CI" below for what it covers.

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

### Install & CI (`scripts/`, `.github/`)

- `scripts/install/` — the numbered sections `install.sh` sources
  (`10-bash.sh` … `70-traefik.sh`), plus `lib.sh` with the shared
  `backup_and_link`/`section_header`/`command_exists` helpers. Adding a section
  means dropping in a new `NN-name.sh`; `install.sh` discovers it by filename,
  and `--list` picks it up with no registration step.
- `scripts/ci/test-install.sh` — the driver CI runs. Executes the real
  `install.sh` end to end, then `assert-symlinks.sh`, then `install_neovim.sh`
  in both `--parsers` and `--queries` modes, a lazy.nvim plugin bootstrap, and
  `test-nvim-highlighting.sh`. Gated behind `DOTFILES_CI_TEST=1` because it
  writes real dotfiles into `$HOME`.
- `scripts/ci/assert-symlinks.sh` — asserts every symlink each install section
  is supposed to create actually resolves back to this repo. Runnable on its own
  against a throwaway `$HOME`.
- `scripts/ci/test-nvim-highlighting.sh` — opens each fixture in
  `scripts/ci/fixtures/` (PHP, TS, TSX, Vue, Rust, JSON, YAML, TOML, HTML, JS,
  shell) in a real tmux + Neovim session and asserts genuine per-token
  treesitter highlighting, rather than Neovim's legacy regex fallback silently
  standing in for it.
- `scripts/ci/stubs/{sudo,systemctl}` — put on `PATH` for the CI run so the
  systemd and pacman-fallback paths execute in a container with no user systemd
  session and no sudoers.
- `.github/workflows/ci.yml` — runs the above on every push, in an
  `archlinux:latest` container with `HOME` forced to `/root` and the checkout
  symlinked to `$HOME/dotfiles` (the hardcoded-path requirement noted under
  Installation).

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

`mcphost` (49 MB), `rg`, `todo-tray`, `phpactor`, `composer`, `phpbrew`, `phpcs`
and `phpcbf` are compiled binaries committed directly to the repo rather than
built from source or installed via package manager — about 68 MB in total, and
worth revisiting.

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

### AI agent config (`ai/`, `.claude/`)

One shared config tree, linked into each agent's own expected location by
`scripts/install/50-ai-tools.sh` — so a skill or hook is written once rather
than per tool.

- `CLAUDE.md` — global cross-project developer context (machine layout, git
  branch model, tooling policy). `AGENTS.md` is the vendor-neutral entrypoint,
  linked to `~/AGENTS.md` and read natively by Codex and Antigravity's `agy`.
  `RTK.md` documents the `rtk` token-saving CLI proxy hook.
- `skills/` — Laravel, Livewire, Pest, OpenCart, Rector, DB, frontend and git
  conventions, plus infrastructure/backup runbooks and an orchestrator-worker
  pattern for multi-agent runs.
- `commands/` — `cherry-pick-to`, `commits`, `project-bootstrap`, and the
  three-command `feature-atlas` toolchain (full scan, single subsystem, report).
- `agents/` — `code-reviewer`, `git-helper`, `legacy-auditor`, `test-writer`,
  and the four `feature-atlas-*` roles (scout, mapper, auditor, synthesizer)
  those commands drive.
- `hooks/` — Pint/PHPStan/Rector/Pest automation on write
  (`laravel-post-write.sh`) and pre-commit (`laravel-pre-commit.sh`).
- `lessons/` — an accumulated store of findings carried between sessions.
- `settings.json`, `statusline-command.sh` — Claude Code settings and a custom
  statusline. **`settings.json` hardcodes an absolute home directory** in its
  hook commands; see Post-install.
- Per-tool adapters over the same content: `agents-opencode/` (opencode's own
  agent format), `codex-skills/` (wrappers importing the shared skills into
  Codex), `gemini-config-skills.json` (points `agy`'s global skill discovery at
  `ai/skills`). Each is linked only if that tool is on `PATH`.

`.claude/settings.local.json` is separate — this repo's own local permission
allowlist, not part of the linked tree. `.mcphost.yml` configures `mcphost`
(local LLM agent host): MCP server definitions and model params.

`.ai/` (distinct from `ai/`) holds this repo's own working notes — `plans/` for
multi-session initiatives and `lessons/` for what they turned up.

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
  (`pull-and-update.sh`, `update-db.py`). Credentials and the DB host live in a
  gitignored `.env`; copy `.env.example` over and fill it in before running
  either the compose file or the script.

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
- `bin/` carries ~68 MB of compiled binaries checked into git rather than built
  or installed normally — `mcphost` alone is 49 MB.
- `scripts/install/50-ai-tools.sh` links `~/.mcphost` to a path that does not
  exist in this repo (the config here is `.mcphost.yml`), leaving a dangling
  symlink, and never links `.mcphost.yml` itself. `assert-symlinks.sh` does not
  catch it: `check_symlink` compares `readlink -f` on both sides, which
  canonicalises a missing final path component instead of failing, so the
  assertion passes on a link pointing at nothing.
- `ai/settings.json` hardcodes an absolute `/home/<user>/` path in 13 hook
  commands, so the Claude Code config is not portable to another username
  without editing.

## Licence

MIT — see [LICENSE](LICENSE).
