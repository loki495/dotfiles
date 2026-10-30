Create a temporary Dibs hand-off so a fresh session can continue this work cold, then give a ready-to-paste prompt that points to it.

**Arguments:** $ARGUMENTS (optional: where to write it, or what to focus on)

---

**Where:** create a task with `todo_create(temporary: true)`, in the project's area and Group, labelled `handoff` (plus `waiting`, `decision needed` or `needs manual verification` when that is why it is parked). Set `parentId` to the permanent plan or task when one exists. Keep durable decisions and plan progress on the permanent record; put transient session state in the temporary hand-off, rather than rewriting a plan body or committing a hand-off file. Temporary tasks never mirror to GitHub and disappear permanently on completion. Temporary parents may have temporary children only; consume children before their parent. If Dibs is unavailable, use a private scratch file outside the public repository and say where it is. Honor an explicit file destination in the arguments. Never put tokens or secrets in either form.

**Body:** the template in skill `session-handoff` — Session, Goal, Why parked, State, Changed since the plan, Next steps, Needs Andres, Open questions, Don't, Cleanup, Docs/atlas, Resume. It is a delta, not a summary: what changed since the plan was last read, and what a cold session must know before touching anything. Durable lessons and decisions go to the plan or a `lesson` / `decision` record first, never only in the hand-off.

**Consumption:** the receiving session reads and claims the temporary task, moves any durable findings to the permanent record, then calls `todo_complete` to delete the hand-off. `reason: NOT_PLANNED` explicitly discards a hand-off whose plan moved on. Normal `todo_release` keeps it for another session. An optional completion summary is copied to the surviving permanent parent and follows that parent's mirroring policy, so keep private hand-off details out of it. Deletion has no undo.

**Finding them later:** `todo_list label=handoff state=OPEN` lists every parked session across all agents and projects.

If Andres wants the next session to start right away, launch it instead of only printing the prompt: `sessioneer --workdir <project dir> --model sonnet --effort medium --mode auto "<the paste-ready prompt>"` (headless Claude, visible and steerable in the Sessioneer dashboard; prints the session name). Always pass `--model sonnet`, `--effort medium` and `--mode auto` unless Andres asks for another (Opus with `--effort high` only when the next session plans or judges). Offer it, don't run it unasked.

Then reply with the temporary task's local id (or the explicit fallback file path) and a short paste-ready prompt: “Read and claim temporary task `<id>`, continue from Next steps, and complete it after consumption; ask about unresolved Open questions.” Durable, general lessons belong in a permanent `lesson`-labeled Dibs record.
