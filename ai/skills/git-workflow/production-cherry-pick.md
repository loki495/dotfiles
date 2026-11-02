# Cherry-picking to production and rebasing `local`

Reference for the `git-workflow` skill; read when the decision tree in `SKILL.md` points here.

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

