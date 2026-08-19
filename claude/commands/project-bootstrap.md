Set up or verify the dev environment for the current project. Run this when starting work on a project for the first time, or when tooling seems missing.

**Arguments:** $ARGUMENTS (optional slug override; defaults to deriving from folder name)

---

## Step 1: Detect project type

```bash
# Laravel: artisan + composer.json with laravel/framework
ls artisan 2>/dev/null && grep -q '"laravel/framework"' composer.json 2>/dev/null && echo LARAVEL

# OpenCart: system/startup.php fingerprint
ls system/startup.php 2>/dev/null && echo OPENCART
```

If neither matches, stop and ask the user what type of project this is.

---

## Step 2: Derive the project slug

The slug drives container names, Traefik hostnames, and the docker-compose `name:` field.

- Default: current folder's basename, lowercased, spaces/dots → hyphens
- Override: use `$ARGUMENTS` if provided
- Examples: `stocker` → `stocker`, `new.example.com` → `client-f-new`

Confirm with the user if it looks ambiguous.

---

## Step 3: Check git layout

```bash
git worktree list
git branch -a
```

If the layout is non-standard (multiple worktrees, unclear which branch is production),
write findings to `.claude/project.md` in the local branch and ask the user to review
before continuing.

---

## Step 4: Gather answers before generating any files

Ask the following questions up-front rather than making assumptions:

**For all projects:**
- PHP version? (check existing `docker-compose.yml` first if it exists; otherwise ask)
- Does a `docker-compose.yml` already exist? If yes, read it and extract slug, container
  name, PHP version, DB setup, and setup script location — skip the generation steps
  for anything already present.
- Where does/should the setup script live?
  - `docker/setup-dev-container.sh` (in a `docker/` subfolder)
  - `setup-dev-container.sh` at the project root
  - Both project types support either location. Default suggestion: `docker/` subfolder.

**For Laravel only:**
- What database will this project use?
  - **MariaDB** via the shared `mariadb-10.5` container (adds `DB_HOST`/`DB_PORT` env
    vars to the compose `app` service)
  - **SQLite** (no DB env vars needed; file is local to the project)
  - **Other** (ask for details)
- Does this project use Vite? (check `package.json` for `@vitejs/plugin-laravel` or
  `vite` in devDependencies — include a `vite` service only if yes)

**For OpenCart only:**
- What PHP version does **production** actually run? (this is critical — match exactly)

---

## Step 5: Generate docker-compose.yml (if missing)

### Laravel

Replace `<SLUG>`, `<PHP_VERSION>`, and apply DB and Vite choices from Step 4.

```yaml
name: <SLUG>

services:
  app:
    container_name: <SLUG>-app
    restart: unless-stopped
    # Only include the environment block if using MariaDB:
    environment:
      DB_HOST: mariadb-10.5
      DB_PORT: 3306
    volumes:
      - ./:/var/www/html
      # Optional: add these if the project uses docker/logs and storage/ssh:
      # - ./docker/logs:/var/www/html/logs:rw
      # - ./storage/ssh:/var/www/html/storage/ssh:rw
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.<SLUG>.rule=Host(`<SLUG>.dev.local.test`)"
      - "traefik.http.routers.<SLUG>.entrypoints=web"
      - "traefik.http.services.<SLUG>.loadbalancer.server.port=80"
    build:
      context: .
      dockerfile_inline: |
        FROM php:<PHP_VERSION>-apache
        # Adjust COPY source based on where the setup script lives:
        COPY docker/setup-dev-container.sh /tmp/setup.sh
        # or: COPY setup-dev-container.sh /tmp/setup.sh
        RUN chmod +x /tmp/setup.sh && /usr/bin/bash /tmp/setup.sh
    networks:
      - web

  # Only include if Vite is confirmed (package.json check):
  vite:
    image: node:20
    container_name: <SLUG>-vite
    working_dir: /var/www/html
    command: ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
    volumes:
      - ./:/var/www/html
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.<SLUG>-vite.rule=Host(`vite.<SLUG>.dev.local.test`)"
      - "traefik.http.routers.<SLUG>-vite.entrypoints=web"
      - "traefik.http.services.<SLUG>-vite.loadbalancer.server.port=5173"
    networks:
      - web

networks:
  web:
    external: true
```

**Notes on the Laravel compose:**
- No `image:` field on the app service (built locally, no need to name the image)
- No `ARG` or `EXPOSE` lines in the dockerfile_inline — the setup script handles everything
- `DB_HOST`/`DB_PORT` env block: include only if using MariaDB; omit entirely for SQLite
- Extra volume mounts (`docker/logs`, `storage/ssh`): optional — add only if the project
  actually uses those paths

### OpenCart

Replace `<SLUG>` and `<PHP_VERSION>` (must match production — ask if unknown).

```yaml
name: <SLUG>

services:
  app:
    build:
      context: .
      dockerfile_inline: |
        FROM php:<PHP_VERSION>-apache
        ARG DEBIAN_FRONTEND=noninteractive
        # Adjust COPY source based on where the setup script lives:
        COPY setup-dev-container.sh /usr/local/bin/setup-dev-container.sh
        # or: COPY docker/setup-dev-container.sh /usr/local/bin/setup-dev-container.sh
        RUN chmod +x /usr/local/bin/setup-dev-container.sh && \
            APACHE_ROOT=. /usr/local/bin/setup-dev-container.sh
        EXPOSE 80
    image: <SLUG>-app
    container_name: <SLUG>-app
    restart: unless-stopped
    volumes:
      - ./:/var/www/html
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.<SLUG>.rule=Host(`<SLUG>.dev.local.test`)"
      - "traefik.http.routers.<SLUG>.entrypoints=web"
      - "traefik.http.services.<SLUG>.loadbalancer.server.port=80"
    networks:
      - web

networks:
  web:
    external: true
```

**Notes on the OpenCart compose:**
- Has `image: <SLUG>-app` (names the built image — consistent with all existing OC projects)
- Has `ARG DEBIAN_FRONTEND=noninteractive` and `EXPOSE 80` in the dockerfile_inline
- `APACHE_ROOT=.` is passed to the setup script so Apache serves from the project root
  (not a `public/` subdirectory like Laravel)
- No Vite service, no DB env vars

---

## Step 6: Create the setup script (if missing)

Both project types can use either location (`docker/` subfolder or project root).
Use whichever location was agreed in Step 4.

**Laravel reference:** `~/www/stocker/docker/setup-dev-container.sh`
Copy this file as the starting point. It handles:
- apt packages (curl, wget, git, vim, openssh-client, image libs, zip)
- PHP extensions: `gd mysqli pdo_mysql zip`
- Apache: `AllowOverride All`, `DocumentRoot /var/www/html/public`, `a2enmod rewrite headers`
- www-data UID/GID fix to 1000
- PHP dev ini (display_errors on, memory_limit 512M, opcache off)
- Xdebug config if xdebug extension is present
- Old Debian release handling (stretch/buster archive mirror fix)

**OpenCart reference:** `~/www/site-a.example.com/client-b-local/setup-dev-container.sh`
This variant uses the `APACHE_ROOT` environment variable to set the Apache DocumentRoot
to the project root (not `public/`). Use it as the OpenCart starting point.

If the setup script already exists at the confirmed location, skip this step.

---

## Step 7: Check and install Laravel tooling (Laravel only)

Get container name from docker-compose.yml, then check each tool:

```bash
CONTAINER=<SLUG>-app

docker exec $CONTAINER test -f ./vendor/bin/pint    && echo "pint OK"    || echo "pint MISSING"
docker exec $CONTAINER test -f ./vendor/bin/phpstan && echo "phpstan OK" || echo "phpstan MISSING"
docker exec $CONTAINER test -f ./vendor/bin/rector  && echo "rector OK"  || echo "rector MISSING"
docker exec $CONTAINER test -f ./vendor/bin/pest    && echo "pest OK"    || echo "pest MISSING"
```

For each missing tool, offer to install (don't install without confirming):

```bash
docker exec $CONTAINER composer require --dev laravel/pint
docker exec $CONTAINER composer require --dev phpstan/phpstan larastan/larastan
docker exec $CONTAINER composer require --dev rector/rector
docker exec $CONTAINER composer require --dev pestphp/pest pestphp/pest-plugin-laravel
docker exec $CONTAINER ./vendor/bin/pest --init
```

---

## Step 8: Scaffold config files (Laravel only, if missing)

### phpstan.neon

```neon
includes:
    - vendor/larastan/larastan/extension.neon

parameters:
    level: 6

    paths:
        - app
        - routes
        - database
        - tests

    excludePaths:
        - bootstrap
        - storage
        - vendor

    bootstrapFiles:
        - vendor/autoload.php

    ignoreErrors:
        - '#Call to an undefined method .*Pest.*#'

    scanFiles:
        - vendor/laravel/framework/src/Illuminate/Foundation/helpers.php
```

Default level is **6**. (stocker is at 4 — older project, not the new default.)

### pint.json

```json
{
    "preset": "laravel"
}
```

### rector.php

```php
<?php

declare(strict_types=1);

use Rector\Config\RectorConfig;
use Rector\Php74\Rector\Closure\ClosureToArrowFunctionRector;
use Rector\Set\ValueObject\LevelSetList;
use Rector\Set\ValueObject\SetList;

return static function (RectorConfig $rectorConfig): void {
    $rectorConfig->paths([
        __DIR__.'/app',
        __DIR__.'/database',
        __DIR__.'/routes',
        __DIR__.'/tests',
    ]);

    $rectorConfig->sets([
        LevelSetList::UP_TO_PHP_83,   // adjust to match the project's actual PHP version
        SetList::CODE_QUALITY,
        SetList::DEAD_CODE,
    ]);

    $rectorConfig->importNames();
    $rectorConfig->importShortClasses(false);

    $rectorConfig->skip([
        ClosureToArrowFunctionRector::class => true,
    ]);
};
```

---

## Step 9: Add composer scripts (Laravel only)

Add to `composer.json` `scripts` section. Replace `<CONTAINER>` with the actual name:

```json
"scripts": {
    "pest":         "docker exec <CONTAINER> ./vendor/bin/pest",
    "pint":         "docker exec <CONTAINER> ./vendor/bin/pint",
    "phpstan":      "docker exec <CONTAINER> ./vendor/bin/phpstan analyse",
    "rector":       "docker exec <CONTAINER> ./vendor/bin/rector process --dry-run",
    "rector:apply": "docker exec <CONTAINER> ./vendor/bin/rector process"
}
```

Merge into any existing `scripts` block — don't replace entries already there.

---

## Step 10: Install the pre-commit git hook (Laravel only)

```bash
ln -sf /home/andres/.claude/hooks/laravel-pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

The symlink means updates to the global hook script take effect in all projects
automatically. If a project-specific override is needed, replace the symlink with a
copy and modify it.

Skip for OpenCart unless `.claude/project.md` explicitly opts in.

---

## Step 11: Summary report

After all steps:
- Project type, slug, container name
- Traefik URL: `http://<SLUG>.dev.local.test`
- Vite URL (if applicable): `http://vite.<SLUG>.dev.local.test`
- Database setup (MariaDB / SQLite / other)
- Setup script location (`docker/` vs root)
- Tools: which were present vs newly installed
- Config files: which were created vs already existed
- Pre-commit hook: installed or skipped
- Git layout notes (if `.claude/project.md` was written)

If the container isn't running yet:
```bash
docker compose up -d --build
```
