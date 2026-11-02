# docker-compose templates (Laravel, OpenCart) and setup script references

Reference for the `project-bootstrap` command, steps 5 and 6.

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
      # No Host() router rule here on purpose - the main app's route lives
      # centrally in the Traefik dynamic config as
      # <SLUG>.${TRAEFIK_DOMAIN}, added separately after this repo exists.
      # This label set just needs enable+port so that central route can
      # find this container.
      - "traefik.enable=true"
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
      - "traefik.http.routers.<SLUG>-vite.rule=Host(`vite.<SLUG>.${TRAEFIK_DOMAIN}`)"
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
      # No Host() router rule here on purpose - the main app's route lives
      # centrally in the Traefik dynamic config as
      # <SLUG>.${TRAEFIK_DOMAIN}, added separately after this repo exists.
      # This label set just needs enable+port so that central route can
      # find this container; it still needs to be on the external `web`
      # network below for Traefik to reach it at all.
      - "traefik.enable=true"
      - "traefik.http.services.<SLUG>.loadbalancer.server.port=80"
    networks:
      - web

networks:
  web:
    external: true
```

If this project is ever meant to also be publicly clonable/distributable (not
just for Andres's own machine), the external `web` network requirement above
will break a fresh clone outright with no pre-existing Traefik network - see
homie's item-1 fix (2026-09-05) for the pattern that solves this: drop the
network/label dependency from the default compose file, publish a host port
instead, and put any Traefik network attachment in a gitignored
`docker-compose.override.yml`. Ask which shape is wanted rather than assuming.

**Notes on the OpenCart compose:**
- Has `image: <SLUG>-app` (names the built image — consistent with all existing OC projects)
- Has `ARG DEBIAN_FRONTEND=noninteractive` and `EXPOSE 80` in the dockerfile_inline
- `APACHE_ROOT=.` is passed to the setup script so Apache serves from the project root
  (not a `public/` subdirectory like Laravel)
- No Vite service, no DB env vars

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

**OpenCart reference:** `~/www/<opencart-site>/<opencart-site>-local/setup-dev-container.sh`
This variant uses the `APACHE_ROOT` environment variable to set the Apache DocumentRoot
to the project root (not `public/`). Use it as the OpenCart starting point.

If the setup script already exists at the confirmed location, skip this step.
