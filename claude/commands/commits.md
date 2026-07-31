List the most recent commits on the current branch with a short description of each.

**Arguments:** $ARGUMENTS

- If a number is provided, show that many commits.
- If no argument is given, default to the last 20 commits.
- If a branch name is provided instead of a number, show the last 20 commits on that branch.
- If both are provided (e.g. `main 10`), show that many commits on that branch.

**Steps:**

1. Run `git log --oneline --decorate -N [branch]` to get the commit list.
2. For each commit, run `git show --stat --format="" <hash>` to get the list of files changed.
3. Present a clean, readable table or list showing:
   - Short hash
   - Commit message
   - Author and relative date (e.g. "2 days ago")
   - Files changed (summary line, e.g. "3 files changed, +42 -7")
4. If on a branch that has diverged from its upstream or a main branch, note how many commits ahead/behind it is.

Keep the output concise — this is meant to be a quick overview, not a full diff.
