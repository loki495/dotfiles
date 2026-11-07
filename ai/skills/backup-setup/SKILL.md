---
name: backup-setup
description: Backs up production cPanel sites (files + databases) and personal projects onto the dedicated backups machine under ~/backups/. Use when setting up, running, or debugging site backups (backup-inmotion2, setup-backup-db-users.py, backup-personal, and the older mysqlbk/pull backup.conf scripts).
---

# Site and project backups

Everything lands in `~/backups/` on the dedicated backups machine, an always-on
laptop on the LAN reached by the SSH alias `backups` (real host, user and port
in `~/.ssh/config`; its login shell is fish, so pipe multi-line commands to
`bash -s`). `~/backups` is its own LVM volume.

## Production cPanel accounts (pull, nightly)

The scripts live in the private dotfiles repo, `~/.dotfiles-private/inmotion/`
(also reachable as `~/www/inmotion-migration/scripts`, a symlink). The backups
machine has its own clone of that repo, and its
`~/backups/bin/backup-inmotion2` is a symlink to `inmotion/backup-inmotion2.sh`
there, so deploying a change is commit, push, then `git -C ~/.dotfiles-private
pull` on the backups machine. It runs from cron at 01:30 under `flock`. For every account of the
cPanel server it writes `~/backups/inmotion2/<acct>/`:

- `files/<date>/`: rsync of the whole home dir (mail, logs, caches and OpenCart `image/cache/` excluded),
  hard-linked against `files/latest` so an unchanged day costs almost nothing.
- `database/<db>-<date>.sql.gz`: one `mysqldump` per database, gzipped on the
  server.
- 30 days of both are kept; logs in `~/backups/logs/inmotion2-<date>.log`
  (summary of ok / skipped / failed at the end).

Accounts it can't SSH into are skipped and listed as `skipped`, not failed.
Read-only from the server's side: nothing on the live site is changed.

One account cannot hold up the rest: every network step is bounded (60 s
reachability probe, 2 h per account, 10 min rsync inactivity, 1 h per dump) and
a failing account is recorded while the loop moves on. A run that fails or skips
anything, or that refuses to start because the laptop has under 5 GB free, mails
`andres@ac495.net` (override with `MAIL_TO`, `MAIL_FROM`, `MAIL_ACCOUNT`). The
message goes over the existing SSH access into the server's Exim, so no mail
password is stored on the laptop.

Databases are dumped as a read-only MySQL user `<acct>_bk` (SELECT, LOCK
TABLES, SHOW VIEW, TRIGGER, EVENT), whose credentials live only in
`~/backups/inmotion2/<acct>/db.cnf` (chmod 600) and travel to the server over
stdin into a temp file. `~/.dotfiles-private/inmotion/setup-backup-db-users.py`
(run on the main machine, which holds the WHM API token) creates the users,
writes `db.cnf` and grants them on every DB the account has. It is idempotent:
**re-run it after an account gets a new database**, or that DB is not dumped
(the dump lists databases at run time but only sees those granted). An account
that has databases (per its own `uapi Mysql list_databases`) but no `db.cnf` is
counted as failed and mails the alert, so a missing dump is never logged as ok.

### Adding an account

1. Shell access on: WHM `modifyacct user=<acct> shell=/bin/bash` (or
   `/usr/local/cpanel/bin/jailshell`); `whm-api.sh` in the same scripts folder.
   Note the account may accept a key and still refuse login until this is done.
2. Authorize the key on the account. The API route works: API2 `SSH::importkey`
   with `name=<label>` and the key, then `SSH::authkey` with `key=<label>.pub`
   (not `name=`, which answers "Invalid filename").
3. `setup-backup-db-users.py <acct>`, add the account to `ACCOUNTS` in
   `backup-inmotion2.sh` if it isn't there, commit, push and pull it on the
   backups machine, then run
   `~/backups/bin/backup-inmotion2 <acct>` once and check the log, the
   snapshot and that each dump ends with `-- Dump completed`.

## Cloudflare DNS (push, nightly)

`backup-dns.py` (systemd user timer `backup-dns`, 03:45) dumps every zone the
Cloudflare token can see to `~/backups/dns/<date>/` on the backups machine: one
JSON file per zone holding the zone metadata and all of its records, plus an
`index.txt` with one line per zone (status, record count, nameservers). Snapshots
are hard-linked, 30 kept, published by `.partial` rename. The token stays on the
main machine at `~/.config/cloudflare/add-zone-edit-dns`; override the path with
`CLOUDFLARE_TOKEN_FILE`. The registrar's own nameservers are not captured.

## Personal projects (push, nightly)

The main machine pushes `~/www/personal` (untracked files included,
`node_modules/` and `vendor/` excluded) to `~/backups/personal/<date>/` on the
backups machine, hard-linked snapshots, 30 kept. Script
`~/.dotfiles-private/backup/backup-personal.sh`, systemd user timer
`backup-personal.timer` (03:30, `Persistent=true` so a missed night runs as
soon as the user session is back). Files a container owns (live MySQL data dirs) can't be read and
are skipped (rsync exit 23 is treated as success); those apps' data needs a
dump of its own.

## Dibs database (push, daily)

A systemd user timer (`backup-dibs.timer`, 03:10, `Persistent=true`) runs
`~/.dotfiles-private/backup/backup-dibs.sh`: `sqlite3 .backup` of the Dibs
database (WAL mode, so never a raw copy), `PRAGMA integrity_check` on the copy,
then rsync to `~/backups/dibs/<date>/` on the backups machine; 30 days kept,
published by `.partial` rename like the personal snapshot.

## Media machine (pull, nightly)

The backups machine pulls the media machine's app config (arr apps, Bazarr,
Jackett, NZBGet, qBittorrent, Home Assistant), `docker` compose and ESPHome
configs, and two small sites over the SSH alias `media` into
`~/backups/media/<date>/`, hard-linked, 30 kept, from cron at 02:30 under
`flock` (script `backup-media.sh` in the private repo's `backup/`, deployed like
`backup-inmotion2`; log `~/backups/logs/media-<date>.log`). SQLite files are
first copied with Python's `sqlite3` backup API on the media machine (no
`sqlite3` binary there) into a temp dir, integrity-checked, pulled and removed,
so live databases are never copied raw. The media library itself is not backed
up. Root-only paths (Pi-hole and tunnel config, Home Assistant's `.storage`, the
Insights docker volume) need sudo there and are a documented manual step in the
private repo's `backup/README.md`. If the key changes, compare the fingerprint
before refreshing `known_hosts` on the backups machine.

## VPS-hosted site (pull, nightly)

One Laravel site runs on its own VPS, not the cPanel server (host and site
names are in the private repo's `backup/README.md`). Its own cron
(`rpc-backup.sh`, 03:15 UTC) dumps the database and tars `storage/app` into
`/bulk/backups` there (7 kept). The backups laptop copies those files into
its folder under `~/backups/` at 04:15 under `flock` (a script in the
private repo's `backup/`, 30 days kept, log in `~/backups/logs/`). It uses a
laptop-only key (not the `id_rsa` the laptop shares with the main machine,
which would then hit the same forced command) that the server locks to
`rrsync -ro /bulk/backups`, so it can read that folder and nothing else.
Its large game media and download folders are not backed up.

## Older per-site scripts (`backup.conf`)

`~/dotfiles/backup-tools/` (`mysqlbk`, `pull`, `full-backup`, `check-backup`)
drive one site per folder from a `backup.conf` (SSH_*, MYSQL_*, LOCAL_*). Not
used for the cPanel accounts above. One gotcha if you do use them: `pull` and
`push` stop when the live site has uncommitted changes, unless
`AUTO_COMMIT_REMOTE="true"`, in which case they run `git add . && git commit
-m "Auto-commit - MM/DD/YYYY"` **on the live site** over SSH. Commit real
in-progress live edits yourself first, and re-fetch any local clone afterwards.
