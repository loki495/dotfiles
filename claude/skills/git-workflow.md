# Git Workflow

## Branch model

```
master/main/stable  — perfect mirror of production
  └── local          — permanent local-only branch, rebased onto master/main
        └── feature  — per-feature branch when multiple things are in flight,
                       rebased onto local, named for the feature
```

- Work directly on `local` when only one thing is in flight. Create a feature branch
  off `local` only when you need to isolate parallel work.
- Local-only changes (debug code, config tweaks, experiments) must never land on
  `master`/`main`/`stable`.
- Remote is usually `origin`. Some projects use `upstream` for the canonical/production
  remote when `origin` is a personal fork — verify before pushing.
- `local` is a per-developer branch-naming convention, not a name one person owns —
  on a shared repo, each teammate may have their own `local` branch. Never push it
  to the shared remote, and never assume a `local` branch (local or on origin)
  belongs to you or should be pulled/merged.

## Cherry-picking to production

Use `/cherry-pick-to` for the standard cherry-pick flow. The intent behind it:

1. Identify the exact commit(s) — inspect with `git log --oneline` if uncertain.
2. Cherry-pick to `master`/`main`/`stable`. Resolve conflicts file-by-file; don't
   use `--strategy-option=theirs` unless you understand what you're discarding.
3. Push `master`/`main`/`stable` to the remote (requires explicit confirmation).
4. Return to `local` (or the feature branch) and rebase onto the updated production
   branch. If feature branches exist, rebase each onto the updated `local` in turn.

Why cherry-pick goes to `master` first (not the other way): `master` must never
contain local-only work. Rebasing `local` onto the updated `master` brings it in sync
without risking that local-only commits slip through.

## Rebase sequences

After any update to `master`/`main`/`stable`:

```bash
git checkout local && git rebase master   # or main/stable
# if feature branches exist:
git checkout feature && git rebase local
```

Resolve conflicts deliberately. If a rebase leaves the repo in a mid-operation state
(`rebase in progress`), describe the state and ask how to proceed before doing
anything else.

## Push safety

- **Never push without explicit confirmation.** Before any push, state: which branch,
  which remote, and whether it's fast-forward or forced.
- If a push to `master`/`main`/`stable` is rejected (non-fast-forward), stop — do NOT
  suggest `--force`. Investigate why (remote has commits not in local?) and fix properly.
- Local-only branches (`local`, feature branches) should never be pushed to the shared
  remote unless the user explicitly wants to share them.
- Before pushing, scan the commits being sent: does any of them contain local-only
  work (debug code, personal config, experiments)? If yes to `master`/`main`/`stable`,
  call it out and stop.

## Concurrent sessions on the same repo

If told (or if context suggests, e.g. uncommitted changes you didn't make) that
another Claude session may be working on the same branch concurrently: only stage/
commit changes you made yourself, don't touch or discard uncommitted work that isn't
yours, and ask before making changes to shared state (branches, files) you didn't
just create — treat unfamiliar in-progress state as someone else's work-in-progress,
not a mess to clean up.

## Discovering an unfamiliar project's layout

Before any git operation on a project not previously touched in this session:

```bash
git worktree list   # are there multiple worktrees?
git branch -a       # what branches exist locally and remotely?
```

If the layout is non-standard or ambiguous, write findings to `.claude/project.md` in
the project (local branch) as a TODO for human review rather than guessing.
