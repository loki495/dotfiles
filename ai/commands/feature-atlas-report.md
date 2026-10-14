Re-validate and re-rank the project's open atlas audit findings, and re-check its open `bug` and
`docs drift` tasks, without rescanning any code beyond the cited evidence. Useful after one or more `/feature-atlas-subsystem` refreshes, or
whenever the ranked list needs to reflect the current state of the code.

**Arguments:** $ARGUMENTS (unused)

---

Atlas location and modes: see `/feature-atlas` ("Where the atlas lives"). Foreground only.

**Workflow steps:**

1. **Require an existing audit** — Dibs mode: the project's open `Feature atlas audit: <Project>
   <date>` parent task in its Group (`todo_search`) with open children. File mode:
   `.ai/feature-atlas/AUDIT-<id>.md` files. If none, tell the user to run `/feature-atlas` and
   accept Phase B first.

2. **Synthesize** — run `feature-atlas-synthesizer` against the parent's open children (their
   bodies are the findings). It re-verifies each against current code, closes or rewrites stale
   and rejected ones (noting why on the task), merges duplicates, re-runs the meta-passes, and
   re-ranks the list in the parent's body (`todo_revise`). File mode: rebuilds `REPORT.md`.

3. **Re-check open findings against the code** — covers every open `bug` and `docs drift` task in
   the project's Group, not only the audit parent's children (see `/feature-atlas`, "Findings").
   For each, read the subsystem id and `Verified at` SHA from its body and run
   `git diff --name-only <sha>..<branch tip> -- <owned_paths>` using the subsystem comment's
   `owned_paths`. If nothing changed, leave the task alone. If an owned path changed, re-read the
   cited `file:line` evidence at the tip and classify the task as still valid (update its
   `Verified at`), fixed, not applicable, or unconfirmed (say what could not be checked). Present
   one batched list of proposed closes (task, classification, the evidence read, a recommendation)
   and close nothing without the user's decision; record the decision on each task.

4. **Handle newly-discovered subsystems** — if it reports `NEW SUBSYSTEM REQUIRED`, tell the user
   those need a mapper-confirmed scout, which this command doesn't run. Offer
   `/feature-atlas-subsystem <name>` for each, or `/feature-atlas` to pick them all up.

5. **Report** — the top priority items from the re-ranked parent and its task id, plus the batched
   close proposals from step 3 awaiting a decision.
