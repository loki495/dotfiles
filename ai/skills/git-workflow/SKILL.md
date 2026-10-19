---
name: git-workflow
description: Git delivery modes (local-only, direct push, PR), branch model (default branch, worktrees, `local` for work projects), cherry-picking to production, push safety, and verifying commit surgery. Use before any non-trivial git operation or push.
---

# Git Workflow

## Delivery mode and branch model

Each repo has a delivery mode, declared on a `Delivery:` line in its `CLAUDE.md`/`AGENTS.md`
and in a guide in its Dibs Group (ask once if missing, then write both):

- **local-only**: no remote; commit on the default branch.
- **direct push**: has a remote you push to (after the push confirmation).
- **PR**: changes reach the default branch only through a pull request. The remote branch name
  is throwaway and doesn't matter; only the PR does.

Branches:

- Small and medium changes are committed directly on the default branch (`master`/`main`).
- Work large enough to disrupt a live site (a checkout that is the running deployment), or
  that must be isolated, goes in a `git worktree` on a temporary branch, merged into the default
  branch locally when done. After the merge, delete the temporary branch, locally and on the
  remote.
- `local` is a permanent branch only for work projects whose production is another machine
  with different paths/credentials. It carries the machine-specific changes and is rebased onto
  the default branch. Personal and this-machine-only projects have no `local`.
- Local-only changes (debug code, config tweaks, experiments) must never land on
  `master`/`main`/`stable`.
- Remote is usually `origin`. Some projects use `upstream` for the canonical/production
  remote when `origin` is a personal fork — verify before pushing.
- Where `local` exists it is a per-developer branch-naming convention, not a name one person
  owns: on a shared repo, each teammate may have their own. Never push it to the shared remote,
  and never assume a `local` branch (local or on origin) belongs to you or should be pulled/merged.

## Cherry-picking to production (repos with a `local` branch)

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

## Rebase sequences (repos with a `local` branch)

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
- Local-only branches (`local`, temporary worktree branches) should never be pushed to the shared
  remote unless the user explicitly wants to share them.
- Before pushing, scan the commits being sent: does any of them contain local-only
  work (debug code, personal config, experiments)? If yes to `master`/`main`/`stable`,
  call it out and stop.
- Also before pushing, read the unpushed log (`git log --oneline origin/<branch>..HEAD`)
  and reorganize it if that would make the history clearer — see "Reorganizing
  unpushed commits" below. After a push, those commits are shared and off-limits.

## Required status check blocks a direct push (GH006)

Several of Andres's repos use a lightweight branch-protection
pattern on `main`: a required status check (their CI's quality job) plus
`enforce_admins`, but no required PR review — direct pushes to `main` are meant
to stay allowed. GitHub still enforces the status check even for a direct push,
though: it checks whether that exact commit SHA *already* has a successful
check run recorded against it, which a brand-new local commit never does yet.
The push is rejected with:

```
remote: error: GH006: Protected branch update failed for refs/heads/main.
remote: - Required status check "..." is expected.
```

This is not the same as the ordinary non-fast-forward rejection above — don't
investigate it as a diverged-history problem, and don't reach for `--force` or
`enforce_admins`-disabling. Fix: get that same commit SHA a green check, then
land it unchanged.

1. Push the commit to a throwaway branch: `git push origin HEAD:refs/heads/<name>`
   (CI on these repos triggers on `pull_request`, not arbitrary branch pushes,
   so a bare branch push alone won't run it).
2. Open a PR against `main` from that branch (`gh pr create --head <name> --base
   main ...`) — this triggers the check.
3. Poll `gh pr checks <number>` until it passes.
4. Merge via `gh pr merge <number> --rebase --delete-branch` — this is the
   sanctioned path. Do **not** try to land it with a raw
   `git push origin <name>:main`: that skips GitHub's merge API entirely and
   reads as a CI-bypass attempt (Claude Code's own auto-mode classifier will
   refuse it for exactly this reason).
5. `--rebase` may give the merged commit a new SHA even with no content change
   (committer date shifts). Sync local `main`: `git fetch origin main`, confirm
   `git diff <old-sha> origin/main` is empty, then `git reset --hard origin/main`.

## Atlas: update and stamp when the work merges into master/main

In a project that has a feature atlas, refresh the subsystems the work touched
(`/feature-atlas-subsystem`) and stamp Verified at when the work lands on the local
`master`/`main`, before any push. For worktree and PR work, merge into the local default branch
first (even in a PR repo, where the PR branch is then prepared from it), stamp with the SHA
there, then push or open the PR. The commit need not be pushed. Whenever you rewrite unpushed
commits (amend, squash, reorder) or a rebase/squash merge (including GitHub's) produces new
SHAs, re-stamp to the resulting SHA. Before working on a repo, compare its GitHub tip (the
atlas's branch) with the atlas's Verified at and refresh if GitHub is ahead. The atlas names
its branch (default: `main`/`master`). Details: the `feature-atlas` command's "Where the atlas
lives".

## After a merge: delete the temporary branch, locally and on the remote

For any merge from a temporary branch (a PR, or a worktree branch merged locally), once it has
merged successfully the branch is finished: delete it in both places and sync the default
branch.

1. Merge with `gh pr merge <number> --rebase --delete-branch` (or the repo's usual merge style
   with `--delete-branch`); that removes the remote branch. Where it was merged some other way,
   `git push origin --delete <branch>`.
2. Switch to the default branch, fetch, and move it to the merged state (`git fetch origin`,
   then fast-forward, or `git reset --hard origin/<default>` only after confirming the local
   default holds nothing unpushed). Rebase merges give the commit a new SHA, so compare content,
   not hashes.
3. Delete the local branch: `git branch -D <branch>` (a rebase merge leaves the original commits
   unreachable from the default branch, so plain `-d` refuses) once the merge is confirmed, then
   `git fetch --prune` to drop the stale remote-tracking ref.
4. Never delete the default branch, a long-lived branch such as `local`, or a branch with an open
   PR or unmerged commits. Do this only after the merge is confirmed, never on a failed or
   unmerged PR. Dependabot branches go with their PRs.

## Splitting accumulated commits into PRs (PR repos)

A PR is a reviewable unit of work: its title and description should let a reviewer
understand "this PR does X, and these changes are necessary to accomplish X." When
the local default branch (or `local`) holds commits for several concerns, group them by concern into separate PRs
(cherry-picked onto temporary branches off `main`), not one PR per commit and not one PR for
everything. Example stack:

```
A  Add GitHub Actions CI
B  Fix CI PHP version matrix
C  Add customer export
D  Add tests for customer export
E  Fix typo in README
F  Refactor unrelated invoice calculation
```

- PR 1 — CI setup: A + B
- PR 2 — Customer export: C + D
- PR 3 — Invoice refactor: F
- E (README typo) can go alone, ride along with a genuinely related PR, or wait for a
  small housekeeping PR.

A mixed PR ("customer export + invoice rounding + CI + README tweak") is harder to
review and looks undisciplined, even though merging it is technically fine. Fixes,
tests and docs for a change stay in that change's PR. Don't overcorrect: tiny
tweaks don't each need their own PR. Propose the grouping to Andres before opening
anything (opening PRs pushes branches; the push confirmation rule still applies).

## Reorganizing unpushed commits

Any commit that has **not been pushed** may be rebased, amended, fixed up, squashed,
combined, split, or reordered freely, to make the history, the grouping of each
feature, and the dependency order between commits clearer. This is encouraged, not
merely tolerated: check the unpushed log (`git log --oneline origin/<branch>..HEAD`)
from time to time, and always before a push, and reshape it when that helps. Typical
reasons: a docs or test fix that belongs in the feature commit it describes (the
"Docs and tests travel with the change" rule in `RULES.md`), a follow-up that
should be part of the commit it fixes, two commits for one feature, one commit
mixing two features, a commit that depends on a later one.

A perfectly ordinary example: read the unpushed log, reorder commits, squash or fix up
a few of them, then reword the main commit, so that one feature's changes are all
together and its fixes, changes of mind, tweaks and bug fixes ship as a single thing
instead of a messy trail. Do it as you go, or just before a push.

Limits:

- A commit that has been pushed to a shared remote stays off-limits without explicit
  confirmation, and rewriting it means a force-push, which is its own separate
  confirmation. Confirm what's pushed (`git branch -r --contains <sha>`) rather than
  assuming.
- Verify every reshaping with the checks in "Verifying commit surgery" below.
- If the worktree has **uncommitted changes that aren't yours**, stop and ask the user
  before touching history — see "Concurrent sessions on the same repo" below.

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

**When history needs reshaping and the worktree holds changes that aren't yours**
(another agent session, running or idle, or the user's own work in progress): ask the
user what to do first, and only proceed with their approval. The safe procedure is:

1. Make a backup commit of the *entire* current state, including the other changes
   (`git switch -c tmp-backup`, `git add -A`, `git commit`), tag it
   (`git tag backup/<topic>-<date>`), then switch back to the real branch and delete
   the temporary branch (`git branch -D tmp-backup`): the tag is the backup, so
   nothing can be lost and no extra branch is left around. Keep the tag until the user
   confirms everything is intact. Never push it (see "Backup tags" below).
2. On the real branch, commit **only your own** changes, and do the reorganization.
3. Restore whatever wasn't yours to the worktree as uncommitted changes (e.g.
   `git checkout backup/<topic>-<date> -- <their files>`, then unstage), and confirm
   with `git diff backup/<topic>-<date>` that the worktree matches what it was, other
   than your own now-committed work.
4. Tell the user what was restored. Once the restore is confirmed (or the backup is no
   longer useful), delete the tag (`git tag -d backup/<topic>-<date>`) — don't leave
   backup tags accumulating, and ask the user before deleting one they haven't
   confirmed.

Never discard, stash away for good, or commit someone else's uncommitted work as if it
were yours.

## Backup tags

A backup is a **local tag**, not a branch: `git tag backup/<topic>-<date> [<commit>]`.
A tag only names a commit, so it can't be checked out into or collect new commits by
accident, doesn't show up in `git branch` output or `git push --all`, and is removed
with one command. Use one before any history surgery worth undoing (rebase, squash,
reset, force-anything), pointing at the current tip; for uncommitted work, make the
snapshot commit first (see above), tag it, and drop the temporary branch.

- **Never push a backup tag.** `git push --tags`, `--follow-tags` and `--mirror` would,
  and it may hold local-only or uncommitted content (a secret, a private path, someone
  else's work in progress). Push branches by name only, and check `git tag -l 'backup/*'`
  is not part of what a push sends.
- Delete it when the work is confirmed intact or it is no longer useful
  (`git tag -d backup/<topic>-<date>`), asking first if it isn't yours.
- Rebase's own `ORIG_HEAD` and the reflog are not a substitute: the first is overwritten
  by the next operation and the reflog expires; a tag stays until you remove it.

## Discovering an unfamiliar project's layout

Before any git operation on a project not previously touched in this session:

```bash
git worktree list   # are there multiple worktrees?
git branch -a       # what branches exist locally and remotely?
```

If the layout is non-standard or ambiguous, write findings to `.claude/project.md` in
the project as a TODO for human review rather than guessing.
