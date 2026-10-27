Create a temporary Dibs hand-off so a fresh session can continue this work cold, then give a ready-to-paste prompt that points to it.

**Arguments:** $ARGUMENTS (optional: where to write it, or what to focus on)

---

**Where:** create a task with `todo_create(temporary: true)`, in the project's area and Group. Set `parentId` to the permanent plan or task when one exists. Keep durable decisions and plan progress on the permanent record; put transient session state in the temporary hand-off, rather than rewriting a plan body or committing a hand-off file. Temporary tasks never mirror to GitHub and disappear permanently on completion. Temporary parents may have temporary children only; consume children before their parent. If Dibs is unavailable, use a private scratch file outside the public repository and say where it is. Honor an explicit file destination in the arguments. Never put tokens or secrets in either form.

**Consumption:** the receiving session reads and claims the temporary task, moves any durable findings to the permanent record, then calls `todo_complete` to delete the hand-off when it is no longer needed. `reason: NOT_PLANNED` explicitly discards it. Normal `todo_release` keeps it for another session. An optional completion summary is copied to the surviving permanent parent and follows that parent's mirroring policy, so keep private hand-off details out of it. Use a brief public-safe note such as “hand-off consumed,” or omit the summary. Deletion has no undo.

**What goes in it:** the current state only. Don't narrate earlier states or approaches that were dropped.

- **Goal:** what we're trying to achieve, in a sentence or two.
- **Current state:** what works now, what's committed (branch and last commit), and what's uncommitted.
- **Decisions agreed:** each decision Andres made this session, stated as a fact.
- **Confirmed lessons:** only things verified for sure (gotchas, hardware facts, commands that work), each marked as verified. Anything still uncertain goes under Open questions, not here.
- **Environment:** the hosts, containers, paths, devices and commands needed to resume.
- **Next steps:** an ordered list, with the very next action first.
- **Open questions:** anything unresolved or unconfirmed.
- **Don't:** things that were tried and ruled out, or that Andres said not to pursue, so the next session doesn't retry them.

If Andres wants the next session to start right away, launch it instead of only printing the prompt: `sessioneer --workdir <project dir> --model sonnet --effort medium --mode auto "<the paste-ready prompt>"` (headless Claude, visible and steerable in the Sessioneer dashboard; prints the session name). Always pass `--model sonnet`, `--effort medium` and `--mode auto` unless Andres asks for another (Opus with `--effort high` only when the next session plans or judges). Offer it, don't run it unasked.

Then reply with the temporary task's local id (or the explicit fallback file path) and a short paste-ready prompt: “Read and claim temporary task `<id>`, continue from Next steps, and complete it after consumption; ask about unresolved Open questions.” Durable, general lessons belong in a permanent `lesson`-labeled Dibs record.
