# PR repos, protected branches, merges

Reference for the `git-workflow` skill; read when the decision tree in `SKILL.md` points here.

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

