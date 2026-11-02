# Atlas stamping at merge

Reference for the `git-workflow` skill (rule 733).

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

Two hooks back this up in Claude Code: the commit gate reminds you of the atlas subsystems a
commit touches and refuses a false `Docs: updated` line, and the push guard denies a push while
a subsystem's owned files changed since its `Verified at`. Fix a denied push by refreshing and
re-stamping those subsystems, not by retrying. Other agents get no hook; the reconciler reports
the same drift.

