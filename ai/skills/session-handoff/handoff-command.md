Create a temporary Dibs hand-off so a fresh session can continue this work cold, then give a ready-to-paste prompt that points to it.

**Arguments:** $ARGUMENTS (optional: where to write it, or what to focus on)

---

**Where:** create a task with `todo_create(temporary: true)`, in the project's area and Group, labelled `handoff` (plus `waiting`, `decision needed` or `needs manual verification` when that is why it is parked). Set `parentId` to the permanent plan or task when one exists. Keep durable decisions and plan progress on the permanent record; put transient session state in the temporary hand-off, rather than rewriting a plan body or committing a hand-off file. Temporary tasks never mirror to GitHub and disappear permanently on completion. Temporary parents may have temporary children only; consume children before their parent. If Dibs is unavailable, use a private scratch file outside the public repository and say where it is. Honor an explicit file destination in the arguments. Never put tokens or secrets in either form.

**Body:** the template in skill `session-handoff` — Session, Goal, Why parked, State, Changed since the plan, Next steps, Needs Andres, Open questions, Don't, Cleanup, Docs/atlas, Resume. It is a delta, not a summary: what changed since the plan was last read, and what a cold session must know before touching anything. Durable lessons and decisions go to the plan or a `lesson` / `decision` record first, never only in the hand-off.

**Consumption:** the receiving session reads and claims the temporary task, moves any durable findings to the permanent record, then calls `todo_complete` to delete the hand-off. `reason: NOT_PLANNED` explicitly discards a hand-off whose plan moved on. Normal `todo_release` keeps it for another session. An optional completion summary is copied to the surviving permanent parent and follows that parent's mirroring policy, so keep private hand-off details out of it. Deletion has no undo.

**Finding them later:** `todo_list label=handoff state=OPEN` lists every parked session across all agents and projects.

**Recommend who picks it up, then ask.** Judge the next steps by work type and take agent, model, effort and (Claude) profile from skill `orchestrator-worker`, `model-routing.md` "Model routing by work type", the same decision `/next` step 4 makes: the highest-ranked entry that is installed, has quota and lists the model; check `sessioneer --usage` first, skip an agent at 90% or more (and the profile whose weekly quota is nearly spent), and the profile is the account the work belongs to (`work` for the Work area, else `personal`). Frontier, or an Opus/advanced tier that only plans or judges, is confirmed with Andres, never chosen alone. State the pick and the one-line reason, then ask with the question tool (the recommended option first, one explanation): start it now with that agent, model and effort; start it with a different agent or model he names; or only print the prompt. Never launch without his answer.

**Pick the prompt's shape from the size of the work.**
- Normal case: the temporary Dibs handoff above, and the prompt only points to it (the paste-ready line below).
- Small work (a few lines, nothing uncommitted, no branch, claim or decision to carry, and nothing parked): skip the Dibs task and give one short self-contained prompt instead: goal, repo and branch, the decisions made, the files, the commands, what is out of scope, what to ask first. Anything that fits that description only; if in doubt, write the Dibs handoff (a session must not end with unfinished work and no handoff task).

If he says start it, launch it: `sessioneer --workdir <project dir> --model <m> --effort <level> --mode auto [--profile <p>] "<the prompt>"` (headless Claude, visible and steerable in the Sessioneer dashboard; prints the session name). `--agent codex` for Codex (no `--profile`; `--mode` only `plan` or `full`). Report the session name, agent, model, effort, profile and workdir. The parked session then holds no claim and can be archived.

Then reply with the temporary task's local id (or the explicit fallback file path; for small work with no task, just the prompt) and a short paste-ready prompt: “Read and claim temporary task `<id>`, continue from Next steps, and complete it after consumption; ask about unresolved Open questions.” Durable, general lessons belong in a permanent `lesson`-labeled Dibs record.
