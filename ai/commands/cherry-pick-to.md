Cherry-pick one or more commits from the current branch into a target branch, push to upstream, then return to the original branch and rebase it. If the target branch has diverged from origin, report the divergence and any conflict risk, and — when it's safe and sensible — `git pull --rebase` the target up to origin before cherry-picking.

**Arguments:** $ARGUMENTS

**Expected format:** `<target-branch> <commit1> [commit2 ...]`  
  OR  
**Natural language:** `<target-branch> <description of which commits to pick>`

- First argument (or first word/phrase up to a recognizable branch name) is the target branch.
- The rest is either a list of explicit commit hashes/refs, or a natural-language description of which commits to pick (e.g. "the last 3 commits", "the fix for the login bug", "everything related to the auth refactor").

**If the commit selection is natural language:**
- Run `git log --oneline -30` (or more if needed) to inspect recent history on the current branch.
- Identify the commits that match the description. Use commit messages, file diffs (`git show --stat`), or author/date context as needed.
- If uncertain between candidates, list them and ask the user to confirm which ones to use before proceeding.

---

**Workflow steps:**

1. **Record state** — capture the current branch name so you can return to it.

2. **Resolve and show what will be cherry-picked** — identify the exact commits (from explicit hashes or by interpreting the natural-language description). Display each as a `git log --oneline` entry so the user can verify. Always ask for confirmation before proceeding.

3. **Switch to the target branch** — `git checkout <target-branch>`. If the branch doesn't exist locally, try `git checkout -t origin/<target-branch>`. If it doesn't exist at all, stop and tell the user.

4. **Sync the target branch with origin (handle divergence before cherry-picking)** — `git fetch origin`, then compare the local target branch to `origin/<target-branch>`:
   - If they're equal, continue to step 5.
   - **If `origin/<target-branch>` has moved ahead (diverged), report it** — show the incoming commits with `git log --oneline <target-branch>..origin/<target-branch>`.
   - **Check and report possible conflicts** — list the files those incoming origin commits touch and compare them against the files touched by the commits you're about to cherry-pick (`git show --name-only`); explicitly call out any overlap as a conflict risk. Overlap does not always mean a real conflict, but it's the signal to slow down.
   - **If it's possible and makes sense, `git pull --rebase` the target branch FIRST, before cherry-picking** — this is the normal case for a production-mirror target branch with no un-pushed local commits: it fast-forwards/rebases the target up to origin's tip so the cherry-pick lands on the latest state. Only do this when the target is a clean tracking branch and the incoming commits don't clearly conflict with the cherry-pick.
   - **Stop and ask** if: the `git pull --rebase` hits conflicts; the target branch has local (un-pushed) commits that make rebasing it risky; there's a reported file overlap that looks like a genuine conflict; or origin can't be reached (in which case ask whether to cherry-pick onto the possibly-stale local target). Never silently resolve conflicts on a production-bound branch.

5. **Cherry-pick the commits** — apply each in order onto the now-synced target branch. If a conflict occurs, stop, show the conflict status, and ask the user how to proceed (resolve manually, skip the commit, or abort the whole operation).

6. **Push to upstream** — before pushing, state the exact branch and remote (`<target-branch>` → `origin`) and get explicit confirmation; commit selection was approved back in step 2, but state can have changed since (rebase, conflict resolution), so confirm again right here. Then `git push origin <target-branch>`. If the push is rejected (non-fast-forward), stop and explain — do NOT force-push without explicit user confirmation.

7. **Return to original branch** — `git checkout <original-branch>`.

8. **Rebase** — run `git pull --rebase` on the original branch. If a rebase conflict occurs, stop and ask the user how to proceed.

9. **Report** — summarize what happened: whether the target branch was synced with origin first (and any divergence handled), which commits were cherry-picked, whether the push succeeded, and the final rebase status.

**Error handling:**
- If arguments are missing or malformed, explain the expected format and stop.
- Never force-push without explicit user approval.
- If cherry-pick or rebase leaves the repo in a mid-operation state, describe the state clearly and ask the user what to do next.
