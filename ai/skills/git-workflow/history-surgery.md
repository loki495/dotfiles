# Rewriting history, backups, concurrent sessions

Reference for the `git-workflow` skill; read when the decision tree in `SKILL.md` points here.

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

