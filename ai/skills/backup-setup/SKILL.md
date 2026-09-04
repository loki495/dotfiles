---
name: backup-setup
description: Backs up a site's git repo + database from its production/live server into ~/backups/<site>/ on the dedicated backups machine. Use when setting up, running, or debugging site backups (mysqlbk, pull, full-backup, backup.conf conventions).
---

# Setting Up Site Backups

Backs up a site's git repo + database from its production/live server into
`~/backups/<site>/` on the dedicated backups machine, reached throughout this
skill by its SSH alias `backups` (define the real host, user and port once in
`~/.ssh/config`). Full variable/script reference:
`~/dotfiles/backup-tools/README.md` on that machine — read it before setting
up a new site, this skill is the workflow, that file is the schema.

## Setting up a new site

1. **Survey a few existing `backup.conf` files first** (`ssh backups "cat
   ~/backups/*/backup.conf"`) — conventions vary (AWS-fleet sites share
   one fleet-wide `.pem`; non-fleet sites use their own key; OpenCart sites add
   `MYSQL_EXCLUDED_TABLES`/`RSYNC_FOLDERS`; etc). Match the closest existing
   pattern rather than inventing a new one.

2. **SSH key**: if the site's server is already on the shared AWS EC2 fleet
   those existing sites use, reuse the fleet key. Otherwise — a new/unrelated
   box — generate a **dedicated keypair on the backups machine**, add the
   public half to the site's own `authorized_keys`. Never reuse an unrelated
   site's key for a box it was never meant for.
   ```bash
   ssh backups "ssh-keygen -t ed25519 -f ~/.ssh/<site>_key -N '' -C 'backups-server -> <site>'"
   # then add ~/.ssh/<site>_key.pub to the site's own authorized_keys
   ```

3. **Create the folder + `backup.conf`** under `~/backups/<site>/` on the
   backups machine (`chmod 600` — it holds a real DB password). Also
   `mkdir -p ~/backups/<site>/database` — nothing auto-creates it before the
   first `mysqlbk` run.

4. **Get the site's real DB credentials** from its own `.env`/config on the
   live server (read-only) — don't guess or reuse another site's.

5. **Run the two commands manually the first time**, from inside the site's
   backup folder, and verify output before trusting it's wired up:
   ```bash
   ssh backups "cd ~/backups/<site> && ~/dotfiles/backup-tools/mysqlbk"
   ssh backups "cd ~/backups/<site> && ~/dotfiles/backup-tools/pull"
   ```
   Check: table count in the dump output matches `SHOW TABLES` count on the
   live DB; `public_html/.git` exists and `git log` on it matches the live
   site's HEAD.

6. **Never touch another site's folder or `backup.conf`** while doing this —
   each is independent; there's no shared state between sites beyond the
   scripts themselves.

## The one non-obvious gotcha: `pull` can create a real commit on the LIVE site

`pull` auto-commits any uncommitted changes it finds on the **remote**
(live) site before pulling — `git add . && git commit -m "Auto-commit -
MM/DD/YYYY"`, run over SSH on the site itself, not a local/backup-side
operation. This is by design (it's how sites with no deploy discipline still
get their live edits captured), but it means:

- Running a backup is not read-only from the live site's perspective. If the
  site had real uncommitted work sitting on it, that work is now a commit in
  its history, with a generic message, not one you wrote.
- If you want descriptive commit messages for a site's in-progress live
  edits, capture and commit them yourself **before** running `pull`/
  `full-backup` — otherwise a routine backup run will beat you to it with a
  generic one.
- After running a backup on a site you're also actively developing against
  elsewhere (a local clone, another branch), re-fetch/rebase there — the
  site's git history may have just moved.

## Orchestration for ongoing (not first-time) backups

`full-backup` = `mysqlbk` + `pull` + `sync-folders.php` +
`check-for-changes-today`, and accepts `--process-subfolders <base-dir>` to
sweep every site under it in one call. `check-backup` is read-only status
(current branch, whether it's behind, most recent dump date) — doesn't back
anything up, safe to run anytime.
