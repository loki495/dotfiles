Refresh a single feature/subsystem's entry in the project's Format v2 atlas — cheap, targeted
version of `/feature-atlas` for when you already know which subsystem changed (e.g. right after
implementing or reviewing a feature) instead of rescanning the whole codebase.

**Arguments:** $ARGUMENTS — a subsystem id or a free-text name/description (e.g. `billing` or
"the notification preferences feature").

---

Atlas location, Dibs mode vs file mode, and the format: see `/feature-atlas` ("Where the atlas
lives"). Everything runs in the foreground.

**Workflow steps:**

1. **Require an existing atlas** — Dibs: `todo_list` label `feature atlas`, the project's parent
   issue; file mode: `.ai/feature-atlas/INDEX.md`. If none exists, tell the user to run
   `/feature-atlas` first; this command refreshes one entry or adds one to an existing atlas, it
   doesn't bootstrap it.

2. **Resolve the subsystem** — match $ARGUMENTS against the index (exact id, then fuzzy against the
   one-line descriptions). If ambiguous, ask. If nothing matches, confirm it's genuinely a *new*
   subsystem, and check its proposed `owned_paths` don't overlap an existing subsystem's.

3. **Staleness check** — `git fetch`, tip = origin default branch. Run the Refresh procedure's
   per-comment diff for this one comment: `git diff --name-only <comment verified-at>..<tip> --
   ':(glob)<p1>' ...` over its `owned_paths` (convert them to pathspecs first if the comment is
   still Format v1). No output: tell the user and ask whether to force a refresh anyway.

4. **Refresh** — run `feature-atlas-scout` for this id: it reads every owned file and test body and
   rewrites the comment in v2 shape, in place (`todo_comment` `commentId` + `expectedRevision`),
   with `verified-at` set to the tip. For a new subsystem, first draft the boundary and
   `owned_paths` pathspecs (tests included) from a quick look at the code and confirm them with
   the user before the scout writes anything; the scout adds a new comment.

5. **Patch the parent** — `todo_revise` the parent body (no `note`): this subsystem's index line
   (and ` (partial)` marker, new comment id if new), and run the coverage diff for new unowned
   files. Verified at advances to the tip only if every other comment is at the tip or unchanged
   since its own SHA (the rule in the mapper's Refresh procedure); otherwise leave it.

6. **Audit follow-up** — if an audit parent `Feature atlas audit: <Project> <date>` exists, tell
   the user its findings for this subsystem may now be stale and offer `/feature-atlas-report`.
