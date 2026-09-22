# Dotfiles

[![Test dotfiles install](https://github.com/loki495/dotfiles/actions/workflows/ci.yml/badge.svg)](https://github.com/loki495/dotfiles/actions/workflows/ci.yml)

Personal dotfiles for an Arch/Garuda Linux desktop (Hyprland + waybar) and a set of
PHP/Laravel/OpenCart dev-tooling scripts. Managed as a single repo, symlinked into
place by `install.sh`.

## Installation

### Prerequisites

Bash and standard Linux file utilities. Neovim downloads also need `curl` and
`tar`; parser installation needs `git`, Node/npm, a C/C++ compiler, and tree-sitter-cli.
The complete desktop setup targets Arch/Garuda. On other Linux distributions or
shared hosting, select the sections you need, for example `./install.sh bash git neovim`.
`bin-tools` can reuse installed ripgrep and Composer on any distribution; automatic
package installation for missing copies uses Arch's `pacman`.

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
   ./install.sh              # default sections; systemd is skipped
   ./install.sh --list       # list available sections
   ./install.sh bash git     # run only the named sections
   ```

`install.sh` is a thin entrypoint: it checks the commands it needs, then runs
each numbered section in `scripts/install/` in order, using a separate Bash
process for each. Each section is also a standalone script (`./scripts/install/10-bash.sh`), so re-running just the one
you touched is the normal way to work here.

| Section | Links / does |
| --- | --- |
| `bash` | `~/.bashrc`, `~/.dircolors` |
| `git` | `~/.gitconfig` |
| `desktop-config` | `~/bin`, and `~/.config/{hypr,waybar,fish,wireplumber}` |
| `systemd` (opt-in) | `~/.config/systemd`, then reloads an available systemd user session |
| `ai-tools` | `~/AGENTS.md` and `~/.claude/*`; also opencode, Codex and Antigravity config, each skipped unless that tool is on `PATH` |
| `neovim` | Installs/verifies Neovim, then links `~/.config/nvim` |
| `traefik` | `~/www/traefik` |
| `bin-tools` | Checks ripgrep/Composer and downloads PHP tools into `~/.local/bin` |

Existing files, directories, and custom symlinks are preserved as `<target>.old`,
then `<target>.old.1`, `<target>.old.2`, and so on. Re-running an unchanged link is
a no-op. Parent directories such as `~/.config` are created when needed, including
when you run a section on its own. The installer does not source your new `.bashrc`;
open a new shell after installation.

The `neovim` section prompts for how to install Neovim itself:

- **User-local:** installs versioned releases under `$HOME/.local/opt/neovim`, symlinked to
  `$HOME/.local/bin/nvim`. Make sure `$HOME/.local/bin` is on `PATH`.
- **Global (needs `sudo`):** installs versioned releases under `/opt/neovim`, symlinked to
  `/usr/local/bin/nvim`.

Set `NVIM_INSTALL_CHOICE=1` (user-local) or `2` (global) to answer that prompt
non-interactively. To install or reinstall Neovim on its own later:
`./install_neovim.sh --user` or `sudo ./install_neovim.sh --global`.

An existing `nvim` is kept only if `nvim --version` succeeds. Use `--force` to
install a new release anyway. Linux x86-64 and ARM64 release assets are selected
automatically; other operating systems/architectures get an explicit error.
Downloads must succeed and the new binary must run before the executable link is
changed. Earlier installations and `~/.local/share/nvim` plugin/parser data are
preserved. The installer writes managed `nvim` and `vim` definitions into
`~/.local/share/dotfiles/neovim.bash` and `neovim.fish`. The repository's Bash and
Fish configs load these after local customizations, overriding stale editor aliases
without editing those customizations. Open a new shell after installation. With
other shell configs, source the matching file at the end of your own local config.
Standalone global installs write aliases for the installing account (root under
sudo); use a user-local install for a shared host. Failed symlink creation restores
the previous target automatically.

**Older glibc / shared hosting:** when a binary cannot run because of glibc,
the installer offers either Neovim's [legacy builds](https://github.com/neovim/neovim-releases)
or a build from source on that host. Upstream labels the legacy builds unsupported.
Both paths check the resulting binary and clean headless startup before changing
the executable link. System glibc is never replaced. Without an interactive
terminal the installer stops with explicit retry instructions:

```bash
./install_neovim.sh --user --legacy
./install_neovim.sh --user --source
# Or through the section installer (choose one):
NVIM_INSTALL_CHOICE=1 NVIM_LEGACY=1 ./install.sh neovim
NVIM_INSTALL_CHOICE=1 NVIM_SOURCE=1 ./install.sh neovim
```

Source builds need working Git, Make, CMake, and C/C++ compilers; Ninja and gettext
are recommended by [upstream's build instructions](https://github.com/neovim/neovim/blob/master/BUILD.md).
The build downloads its dependencies and uses two jobs by default; set
`NVIM_BUILD_JOBS` to adjust this for a shared host. A user-local build does not need
sudo, but the host must provide compatible build tools. It builds the current
stable release into a separate directory and preserves previous installs on failure.

Application installs do not install plugins or treesitter parsers. Parser/query
commands now exit nonzero if any requested language fails, while keeping successful
installs. On a non-Arch host, install the required build tools with your package
manager first.

### Rerunning the installer

Matching config symlinks are left alone. Replaced configs remain in numbered
`.old` backups; they are not merged into the new active configuration. A working
Neovim binary is skipped unless `--force` is specified. Forced binary installs
keep older versions and executable backups.

Parsers, queries, generated aliases and downloaded tools use atomic replacement.
Identical files are skipped; changed files are preserved under a sibling
`.dotfiles-backups/` directory, with numbered backups. Keep personal query overrides
in `nvim/after/queries/` rather than editing generated query files. Parser builds
still run on repeat, so rerunnable does not mean no network or build work.
`--node-provider` is an npm-managed dependency update and can change its package
files; it is not a general-purpose backup of that directory.

The default installer changes desktop, Git and AI configuration as well as Neovim.
To update only highlighting, use `--parsers` and `--queries`. Preserving old files
does not mean all custom settings stay active after a config is replaced.

### Native syntax highlighting

Neovim 0.12+ runs highlighting through `vim.treesitter`, without the
nvim-treesitter plugin. Install the external grammars and their queries together:

```bash
./install_neovim.sh --parsers
./install_neovim.sh --queries
```

This covers Bash, Markdown, PHP, JavaScript/JSX and Blade, alongside the existing
HTML, CSS, YAML, TypeScript/TSX, Vue, JSON, Rust and TOML setup. Markdown uses
Neovim's bundled parsers and queries. Blade keeps the `php` filetype for PHP tools,
but uses its own grammar for highlighting. Embedded PHP, HTML, JavaScript and CSS,
Bash heredocs and Markdown code fences are checked with representative fixtures.

External grammars and query assets are pinned together in
`scripts/install/treesitter-versions.sh`. Most queries are data from a compatible
archived nvim-treesitter snapshot; Blade uses matching upstream grammar/query
revisions. The archived plugin's Lua code is never loaded. Inherited query files
such as `php_only`, `ecma`, `jsx` and `html_tags` are installed automatically.
Two small native query directives handle heredoc language names and script MIME
types. Update pins together and run the capture tests when upgrading these assets.

Missing or incompatible parsers/queries produce a warning and fall back to regular
syntax highlighting. Restart Neovim after replacing parsers. Use `:Inspect` to
check token captures and `:InspectTree` to inspect embedded-language parsing.
Indentation and textobjects are outside this highlighting setup.

### Post-install

- **Neovim:** plugins install automatically on first run via lazy.nvim. The Wilder
  plugin also needs Python 3 and its `pynvim` provider (`python-pynvim` on Arch).
  Tailwind Tools also uses the Node provider. With working Node.js and npm, run
  `./install_neovim.sh --node-provider` to install it under your home directory
  without sudo or a global npm install. Neovim loads this host before plugins.
  This separate step keeps binary-only installation usable on hosts without Node.
  Existing plugin installations should run `:UpdateRemotePlugins` afterwards.
  For a fresh setup, run `nvim --headless "+Lazy! sync" +qa` to finish plugin builds.
- **Claude Code:** `ai/settings.json`'s hook commands use `$HOME`, portable to any
  username. Personal hooks (referencing a separate, private `sessioneer` checkout)
  live in your own **global** `~/.claude/settings.local.json` instead — not this
  repo's project-scoped `.claude/settings.local.json` (see below), a different file
  Claude Code also merges in, but only for sessions run inside this repo. Copy
  `ai/settings.local.json.example`'s `hooks` block into the global one if you use
  `sessioneer` too; nothing here assumes it exists.
- **Systemd and OpenCode:** default installation never reloads systemd or starts
  services. AI-tool configuration links can be installed on shared hosts without
  systemd. To opt in on a desktop with a running user session:
  ```bash
  ./install.sh systemd
  # Review your units first; starting OpenCode is a separate explicit action:
  systemctl --user enable --now opencode-serve.service
  ```
  Explicit systemd setup checks the user session before modifying configuration.
  Hosts without one get a clear error. This does not disable any services you
  previously enabled.

## Tests

Fast offline regression tests cover broken binaries, old-glibc errors, rejected
downloads, preserved data/backups, missing directories, argument handling, and
parser/query failures. They refuse to run outside a disposable Docker container:

```bash
docker build -t dotfiles-installer-tests - <<'EOF'
FROM node:22
RUN apt-get update -qq && apt-get install -y -qq fish
EOF
docker run --rm --network none -e DOTFILES_TEST_CONTAINER=1 \
  -v "$PWD:/repo:ro" dotfiles-installer-tests python3 /repo/tests/test_installers.py
```

The full install/highlighting suite below also requires a throwaway container:

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
  `autocmds.lua`, `highlighting.lua` (native Tree-sitter), `functions.lua` (custom user commands), `php_dev.lua` (helpers
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

- `scripts/install/` — the numbered sections `install.sh` runs
  (`10-bash.sh` … `80-bin-tools.sh`), plus `lib.sh` with the shared
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
- `scripts/ci/test-native-highlighting.lua` — checks actual token captures and
  language injections for the five common file types, plus diagnostic fallback
  when parsers or queries fail. Runs without the plugin manager.
- `scripts/ci/test-nvim-highlighting.sh` — opens each fixture in
  `scripts/ci/fixtures/` (PHP, TS, TSX, Vue, Rust, JSON, YAML, TOML, HTML, JS,
  shell, Markdown, Blade) in a real tmux + Neovim session and asserts genuine per-token
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
`tmux-sessions`), a Docker SQL-import helper (`import-sqlgz-files-docker.sh`),
an email notifier (`notify-email`, via curl's SMTPS support — see
backup-tools/README.md), and misc desktop scripts (`new-reddit-wallpaper`,
`dmenu-clear-cache`, `pushbullet-message`, `open-nvim`).

`rg`, `phpactor`, `composer`, `phpbrew`, `phpcs`, and `phpcbf` are fetched by
`scripts/install/80-bin-tools.sh` rather than committed — `rg` and `composer`
via pacman, the rest as standalone release binaries/phars. `todo-tray` stays
committed (2.3 MB, personal Qt tool with no other surviving source) — see
"Known rough edges". `mcphost` and its wrapper `boost-query.sh` were removed
outright: both were a one-night experiment (Aug 2025) never actually adopted,
and mcphost's own upstream is now archived/dead anyway.

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

### AI agent config (`ai/`)

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
- `settings.json`, `settings.local.json.example`, `statusline-command.sh` — Claude
  Code settings and a custom statusline, portable (`$HOME` throughout).
  `settings.local.json.example` is a copyable template for personal hooks
  (referencing a separate `sessioneer` checkout) that intentionally live outside
  this repo, in your global `~/.claude/settings.local.json`; see Post-install.
- Per-tool adapters over the same content: `agents-opencode/` (opencode's own
  agent format), `codex-skills/` (wrappers importing the shared skills into
  Codex), `gemini-config-skills.json` (points `agy`'s global skill discovery at
  `ai/skills`). Each is linked only if that tool is on `PATH`.

This repo's own root-level `.claude/settings.local.json` is separate again from both
of the above — Claude Code's project-scoped local permission allowlist, applying only
to sessions run inside this checkout, not part of the linked `ai/` tree, and unrelated
to your global `~/.claude/settings.local.json`.

`.ai/` (distinct from `ai/`) holds this repo's own working notes — `plans/` for
multi-session initiatives and `lessons/` for what they turned up.

### Traefik (`traefik/`)

Symlinked to `~/www/traefik/` (the live reverse-proxy config for the whole
home lab: routes both this machine's Docker-labeled containers and `media`'s
own services — Sonarr, Radarr, etc. — via the file provider, and issues a
wildcard cert for the home domain through Let's Encrypt DNS-01 against
Cloudflare). `docker-compose.yml` runs Traefik itself; `dynamic/` holds the
file-provider routes (`ac495-sites.yml`) — a former one-off self-signed TLS
cert for sessioneer (`csm-tls.yml`, needed before the real wildcard cert
existed) was removed once the wildcard cert made it redundant.
`cloudflared-media-config.yml` is the Cloudflare Tunnel ingress config that
actually runs on `media`; it holds real ingress/credential detail, so it is
gitignored and only its `*.example` counterpart is checked in.

`docker-compose.yml` and `dynamic/ac495-sites.yml` *are* committed, with the
domain templated as `{{ env "TRAEFIK_DOMAIN" }}` rather than written out. The
routes that shouldn't be public live in `dynamic/local-sites.yml`, which is
gitignored. Traefik's file provider watches the whole `dynamic/` directory
(`--providers.file.directory=/dynamic`, `--providers.file.watch=true`) and
merges every `.yml` in it, so splitting the routes across two files costs
nothing at runtime — the committed file carries the routes I don't mind
publishing, the ignored one carries the rest.

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
- `install_neovim.sh` hardcodes the download for `linux-x86_64` — detecting
  the real OS/arch (`uname -s`/`uname -m`) would make it work on other
  architectures too.

## Licence

MIT — see [LICENSE](LICENSE).
