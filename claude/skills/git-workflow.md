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

## Verifying commit surgery (splits, amends, reorders)

Whenever reshaping history — splitting a commit, amending one, pulling stray files
back into the commit they actually belong to, reordering — verify the result matches
before trusting it, rather than eyeballing the diff:

1. **Before touching anything**, make sure the working tree reflects the correct
   final content. If there are unstaged/uncommitted changes, capture them as a
   temporary commit first (`git commit -am "wip: temp snapshot for diff
   verification"`) — this becomes the ground-truth diff target for the whole
   operation. If the tree is already clean and committed, that commit itself is the
   diff target — no separate temp commit needed.
2. Do the surgery: interactive rebase with `edit`, `commit --amend`, or `reset` +
   selective `git add -p`/`git reset -p` to split hunks between commits when a
   single commit mixes content that belongs in two different results.
3. **Compare the result against that diff target** — `git diff <target> HEAD` (or
   compare tree hashes) — rather than assuming the surgery worked. It should come
   back empty, or show only the specific intended change.
4. Once confirmed identical, drop any temporary snapshot commit — it was only
   scaffolding for the comparison (`git reset --soft` it away, or drop it in the
   same rebase).

This applies any time commits need reshaping — fixing a commit another
process/session swept unrelated files into, splitting an overly broad commit, or
reordering before push. Read "Concurrent sessions on the same repo" below before
rewriting any commit you didn't author yourself, and never rewrite a commit already
pushed to a shared remote without explicit confirmation — it requires a force-push,
which is its own separate confirmation even after the rewrite itself is approved.

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
