---
name: git-workflow
description: Git delivery modes (local-only, direct push, PR), branch model (default branch, worktrees, `local` for work projects), cherry-picking to production, push safety, and verifying commit surgery. Use before any non-trivial git operation or push.
---

# Git Workflow

Core only. Hard rules live in Dibs rules (injected by the rule-inject hook; other agents grep
`ai/rules.md`): push confirmation [734], no rewrite of pushed commits [735], delete temporary
branches after a merge [736], commit only your own paths [739], delivery mode [731], atlas at
merge [733], docs/tests with the change [732], no `Claude-Session:` trailer [738].

## First: know the repo

Before any git operation on a project not yet touched this session run `git worktree list` and
`git branch -a`. Layout non-standard or ambiguous: write the findings to `.claude/project.md` as a
TODO for human review instead of guessing.

## Delivery mode (a `Delivery:` line in the repo's `CLAUDE.md`/`AGENTS.md`; ask once if missing, write it down)

- **local-only**: no remote; commit on the default branch.
- **direct push**: push to the remote after the push confirmation.
- **PR**: changes reach the default branch only through a pull request; the remote branch name is throwaway.

## Branch model

- Small and medium changes: commit directly on the default branch (`master`/`main`).
- Work that could disrupt a live checkout, or must be isolated: a `git worktree` on a temporary
  branch, merged locally when done, then delete the branch locally and on the remote.
- `local` exists only for work projects whose production is another machine with different
  paths/credentials; it carries machine-specific changes and is rebased onto the default branch.
  Per-developer name: never push it to a shared remote, never assume someone else's `local` is yours.
- Debug code, config tweaks and experiments never land on `master`/`main`/`stable`.
- Remote is usually `origin`; some projects use `upstream` for production when `origin` is a fork: verify.

## Commits

Commit after each discrete task, or a few tightly related items as one themed commit; keep commits
feature-scoped; don't leave verified work uncommitted while unrelated work piles up. This is
cadence once committing, not permission to commit unprompted.

## Decision tree

- **Pushing** → state branch, remote, fast-forward or forced, get confirmation [734]. Scan the
  outgoing commits for local-only work (stop if any would reach `master`/`main`/`stable`). Read
  `git log --oneline origin/<branch>..HEAD` and tidy it first. Rejected non-fast-forward: stop, never
  suggest `--force`; find out why. Never push `local` or worktree branches unless asked.
- **Push rejected with GH006 (required status check)**, **opening or merging PRs**, **after a merge
  (branch cleanup)**, **grouping commits into PRs** → `pr-and-merge.md`.
- **Reshaping unpushed commits** (amend, squash, reorder, split), **verifying the result**, **tree has
  changes that aren't yours**, **backup tags** → `history-surgery.md`. Pushed commits are off-limits
  without confirmation; a rewrite is a force-push and a separate confirmation.
- **Cherry-pick to production, rebasing `local`** (repos with `local`; `/cherry-pick-to`) →
  `production-cherry-pick.md`. Order: cherry-pick to `master` first, push (confirmed), rebase `local` onto it.
- **Work merged into the default branch and the project has a feature atlas** → `atlas.md`
  (rule 733: write a hint line, never refresh by hand).
- **Mid-operation state** (`rebase in progress`): describe it and ask before doing anything else.
- **Another session may be in the same repo / uncommitted changes you didn't make**: stage only
  your own paths, touch nothing else, ask before reshaping history (`history-surgery.md`).
