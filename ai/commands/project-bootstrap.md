Set up or verify the dev environment for the current project. Run this when starting work on a project for the first time, or when tooling seems missing.

**Arguments:** $ARGUMENTS (optional slug override; defaults to deriving from folder name)

Templates live in `~/dotfiles/ai/reference/project-bootstrap/`: `compose-templates.md` (docker-compose
for Laravel and OpenCart, setup-script references) and `laravel-tooling-configs.md` (phpstan.neon,
pint.json, rector.php, composer scripts). Read the one a step names only when you reach it.

## Step 1: Detect project type

```bash
ls artisan 2>/dev/null && grep -q '"laravel/framework"' composer.json 2>/dev/null && echo LARAVEL
ls system/startup.php 2>/dev/null && echo OPENCART
```

Neither matches: stop and ask what type of project this is.

## Step 2: Derive the project slug

The slug drives container names, Traefik hostnames and the compose `name:`. Default: the folder's
basename, lowercased, spaces/dots to hyphens (`new.example.com` → `new-example`); `$ARGUMENTS`
overrides. Confirm with the user if ambiguous.

## Step 3: Check git layout

`git worktree list` and `git branch -a`. Non-standard layout (several worktrees, unclear
production branch): write findings to `.claude/project.md` in the local branch and ask the user to
review before continuing.

## Step 4: Gather answers before generating any files

Ask up front, do not assume.

All projects: PHP version (check an existing `docker-compose.yml` first); whether a
`docker-compose.yml` exists (if so read it, extract slug, container, PHP version, DB, setup-script
location, and skip generation for what is present); where the setup script lives (`docker/`
subfolder, default suggestion, or project root; both types support either).

Laravel only: database (shared `mariadb-10.5` container, which adds `DB_HOST`/`DB_PORT` env vars to
the `app` service; SQLite, no env vars; or other, ask), and whether it uses Vite (check
`package.json` for `@vitejs/plugin-laravel` or `vite`; include a `vite` service only if yes).

OpenCart only: the PHP version production actually runs (critical, match exactly).

## Steps 5 and 6: Generate docker-compose.yml and the setup script, each only if missing

Use `compose-templates.md` (substitute `<SLUG>`, `<PHP_VERSION>`, apply the Step 4 choices). Keep
its notes: if the project may ever be publicly cloned, the external `web` network breaks a fresh
clone; ask which shape is wanted (default compose publishes a host port, Traefik attachment goes in
a gitignored `docker-compose.override.yml`).

## Step 7: Check and install Laravel tooling (Laravel only)

With `CONTAINER=<SLUG>-app`, check each of pint, phpstan, rector, pest:
`docker exec $CONTAINER test -f ./vendor/bin/<tool> && echo OK || echo MISSING`.
For each missing tool offer to install (never without confirming):

```bash
docker exec $CONTAINER composer require --dev laravel/pint
docker exec $CONTAINER composer require --dev phpstan/phpstan larastan/larastan
docker exec $CONTAINER composer require --dev rector/rector
docker exec $CONTAINER composer require --dev pestphp/pest pestphp/pest-plugin-laravel
docker exec $CONTAINER ./vendor/bin/pest --init
```

## Steps 8 and 9: Scaffold config files and composer scripts (Laravel only, if missing)

Use `laravel-tooling-configs.md`: phpstan.neon (default level 6), pint.json, rector.php; merge the
composer scripts into any existing `scripts` block without replacing entries.

## Step 10: Pre-commit git hook (Laravel only)

```bash
ln -sf ~/.claude/hooks/laravel-pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

The symlink makes updates to the global hook apply everywhere; replace it with a copy only for a
project-specific override. Skip for OpenCart unless `.claude/project.md` opts in.

## Step 11: Summary report

Project type, slug, container; Traefik URL `http://<SLUG>.${TRAEFIK_DOMAIN}` (once a route exists in
the Traefik dynamic config) and Vite URL `http://vite.<SLUG>.${TRAEFIK_DOMAIN}` if applicable;
database; setup script location; tools present vs newly installed; config files created vs
existing; pre-commit hook installed or skipped; git layout notes. Container not running yet:
`docker compose up -d --build`.
