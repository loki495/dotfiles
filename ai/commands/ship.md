Commit finished work and get it where it belongs (pushed, cherry-picked to production, propagated, or opened as a PR), using this repo's own shipping flow. Asks once before anything leaves the machine.

**Arguments:** $ARGUMENTS (optional: what to ship, e.g. "the login fix", or a flow override like "as a PR")

---

**1. Find this repo's shipping flow.**

Look for a `## Shipping` section in the project's `CLAUDE.md` (or `.claude/project.md`). If it exists, follow it. If it doesn't, work it out: run `git branch -a`, `git worktree list` and `git remote -v`, and check `gh repo view --json defaultBranchRef,isFork` plus branch protection if `gh` is available. Then propose one of these flows and ask which is right. Don't guess, because repos and groups differ:

- **Cherry-pick to production:** commit on `local` (or a feature branch), cherry-pick to `master`/`main`/`stable`, push that, then rebase `local` back onto it (the `git-workflow` skill's standard model; reuse `/cherry-pick-to` for the mechanics).
- **Propagate from a common root:** commit on the shared root branch, then merge or cherry-pick it into each dependent branch (e.g. per-site or per-client branches) and push each.
- **Branch + PR:** push a feature branch and open a GitHub PR (`gh pr create`). Use this for repos with protected default branches, required checks, or other contributors.
- **Direct push:** commit and push the current branch to its upstream.
- **Custom:** whatever else the repo needs; capture the exact steps.

Once confirmed, write the flow into a `## Shipping` section of the project's `CLAUDE.md` (branch names, remotes, target branches, PR base, any last-minute `git pull --rebase` step). Include it in the same commit as the work being shipped, so the next `/ship` doesn't ask again.

**2. Commit.**

Run `git status`. Stage only this session's changes. If there are uncommitted changes that aren't yours, stop and ask (see the `git-workflow` skill's Concurrent sessions section). Follow the global commit rules: feature-scoped commits, docs and tests in the same commit, and no `Claude-Session:` trailer. Review `git log origin/<branch>..HEAD` and fold fix-ups into the commit they belong to before shipping.

**3. Confirm once.**

Show the plan in one message: the commits (`git log --oneline`), the flow, and every exact `branch → remote` push or PR target. Get explicit confirmation. That one confirmation covers the agreed mechanical steps that follow, but stop and re-ask if anything changes: a conflict, a diverged remote, or a rejected push.

**4. Ship.**

Run the flow. Fetch first and handle divergence as `/cherry-pick-to` does. Never force-push without explicit confirmation. Stop on any conflict and describe the state.

**5. Report.**

Say what was committed, where each commit landed (branch, remote, PR URL), and the final state of every branch touched.
