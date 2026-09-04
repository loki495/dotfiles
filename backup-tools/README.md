# backup-tools

Pulls git repos + MySQL dumps from remote sites into `~/backups/<site>/`,
one subfolder per site. Run from inside a site's backup folder (or pass
`--process-subfolders <base-dir>` to `full-backup`/`check-backup` to sweep
every site under a base dir).

## `backup-tools.conf` (machine-specific, gitignored)

`backup_crons.sh`, `check-hd-space full`, and `common-git` read their site
lists and base paths from `backup-tools.conf` in this directory. It is
gitignored — the site list is client infrastructure and doesn't belong in a
public repo — so a fresh clone has to create it first:

```bash
cp backup-tools.conf.example backup-tools.conf
$EDITOR backup-tools.conf
```

Scripts that need it exit with a clear message if it's missing. See
`backup-tools.conf.example` for the full set of variables.

## `backup.conf`

Each site's folder needs a `backup.conf` (bash, sourced directly — `# vi: ft=bash`
at the top for syntax highlighting). Surveyed across ~44 sites' actual conf
files; not every variable is used by every site.

**Required:**
- `SSH_HOST`, `SSH_USER` — remote box to pull from.
- `SSH_KEY` — private key path. Prefer a **dedicated key per site** when the
  site isn't on the shared AWS EC2 fleet (`ec2-fleet.pem` is shared across
  many sites that *are* on that fleet — don't reuse it for an unrelated box).
- `SSH_BASE_PATH` + `SSH_PATH` — concatenated to the remote code directory.
- `LOCAL_BASE` (almost always `` `pwd` ``) + `LOCAL_PATH` (almost always
  `public_html`) — where the git clone lands locally.
- `MYCNF_PATH` — remote home dir; a `.my.cnf.<database>` gets written there
  (auto-created by `check_mycnf` in `bash/lib/common` on first run).
- `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`.

**Optional:**
- `SSH_PORT` — omit for default 22.
- `MYSQLDUMP_FILE` — only consumed by the **old** single-file `mysqlbk`
  (see below); the current per-table version ignores it and computes its own
  path. Still worth setting for consistency/history, but don't assume
  changing it affects where dumps actually land today.
- `MYSQL_EXCLUDED_TABLES=(table1 table2 ...)` — skip these tables entirely.
- `UPSTREAM_GIT_BRANCH` — defaults to `master` if unset (see `common-git`).
- `SITE_DOMAIN`, `SITE_HTTPS`, `SITE_TYPE` (`laravel`/`opencart`/`wordpress`/
  `cta`) — informational / used by a few of the other scripts (e.g.
  `clone-site`'s WordPress URL fixup); not required for `pull`/`mysqlbk`.
- `RSYNC_FOLDERS` — extra folders to sync outside git (OpenCart sites use
  this for `image/` uploads that aren't tracked in their repo).
- `NO_MYSQL=1` — skip the DB backup entirely for this site.
- `GIT_DIR` / `GIT_WORK_TREE` — only for a bare-repo remote setup (one site
  uses this; everything else is a normal working-tree repo with `.git` inside
  the code dir).
- `DRIVE`, `DRIVE_MIN` — disk-space check thresholds (used by `check-hd-space`).

## `pull` auto-commits on the REMOTE before pulling — know this going in

`pull` (via `common-git`'s `git_commit()`) checks the remote site for
uncommitted changes and, if any exist, runs `git add . && git commit -m
"Auto-commit - MM/DD/YYYY"` **on the remote** before pulling. This is by
design — it's how a site with no deploy discipline (direct edits on the
live box) still gets its work captured — but it means:

- A backup run can create a real commit on the site's own repo with a
  generic message, bundling together whatever was uncommitted at that
  moment, however unrelated. It is *not* a no-op/read-only operation.
- If you want descriptive, reviewed commit messages for a site's live
  edits, capture and commit them yourself *before* running a backup that
  would otherwise catch them in a generic auto-commit.
- This also means a site with `receive.denyCurrentBranch=updateInstead`
  configured (so pushes deploy directly) is unaffected by this — auto-commit
  and push are unrelated mechanisms — but it's still worth knowing a backup
  run just changed the site's git history before assuming why a new commit
  appeared there.

## `mysqlbk`: per-table parallel dump (current) vs. single-file (old)

The current `mysqlbk` dumps **one gzip file per table**, 4-way parallel
(`MAX_PARALLEL=4`), into `database/<YYYY-MM-DD>/<database>:<table>.sql.gz`.
Routines/events are explicitly skipped per-table (`--skip-routines
--skip-events` — redundant across every table's dump otherwise) but
triggers are kept. It lists tables itself via `SHOW TABLES` rather than
letting a single `mysqldump --databases` call handle everything, so
`MYSQL_EXCLUDED_TABLES` is matched against that list before dumping.

`mysqlbk.old-single-dump` is the previous version (single `mysqldump |
gzip` to the literal `$MYSQLDUMP_FILE` path) — kept for reference/rollback,
not run by anything.

If a table's dump fails (auth issue, disk full, network drop mid-transfer),
`mysqlbk` no longer reports success anyway: it detects the real exit code
through the `mysqldump | gzip` pipe, renames that table's output to
`<table>.sql.gz.FAILED` so it can't be mistaken for a good backup, and
keeps dumping the other tables in parallel rather than aborting the whole
run. Once all tables are done, if anything failed it prints a summary and
sends **one** aggregated email (not one per table) via `bin/notify-email`,
then exits non-zero.

## Email notifications

`bin/notify-email <subject> <body> [recipient]` sends mail via curl's
native SMTPS support against Gmail — no local MTA or extra package needed,
since curl is already a hard dependency of this whole toolkit. Requires
`GMAIL_PASSWORD` (a Gmail App Password for you@example.com) in
`~/dotfiles/.env` (gitignored, per-machine — not something `install.sh`
can set up for you). Used by `mysqlbk` (table dump failures),
`check-hd-space` (low disk space), and `check-for-changes-today`
(undocumented changes on the remote site).

## Orchestration

`full-backup [--process-subfolders] <path>` = `mysqlbk` + `pull` +
`sync-folders.php` + `check-for-changes-today`, per site. `check-backup`
is a read-only status check (branch, whether master is behind, most recent
database dump) — doesn't back anything up.
