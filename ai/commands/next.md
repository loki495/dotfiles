Check this session's context and quota, clean up, then take the next step: continue here, or launch a fresh session with the right profile, model and a minimal prompt.

**Arguments:** $ARGUMENTS (optional: a plan id, or a short description of the next piece of work when there is no Dibs plan)

---

## 1. Measure

- Context size: the current session's token count (the status line, or the transcript size).
- `sessioneer --usage`: per profile (`personal` is `~/.claude`, `work` is `~/.claude-work`), the `session` and `week_all` percentages and when they reset.
- Pick the plan: the argument, else the plan of a task this session holds a claim on (`todo_claim_status`), else ask. With no Dibs plan, the next step is whatever Andres described or the open items of the conversation.

## 2. Clean up (always, before continuing or launching)

Do these now even if they "should already be done"; report in one line what was already clean.

- **Claims:** complete (`todo_complete` with evidence) or release (`todo_release` with what is left and the exact next step) every claim this session holds.
- **Records:** update the plan body and the finished step (commit SHA, what is next, what blocks it), file follow-ups you noticed, close finished tasks, update the `lesson`/`research` records the work changed.
- **Docs, tests and atlas:** anything the committed work makes wrong is fixed in the repo; touched atlas subsystems updated and stamped with the SHA on master/main.
- **Files:** delete scratch files, temp scripts, `/tmp` outputs, stray state files and temporary branches or worktrees this session created (look at each before deleting; leave anything that is not yours). Backup tags only if the work is confirmed intact.
- **Peers:** `sessioneer --peers`; tell any peer working on the same repo what changed.
- **Nothing pushed without Andres:** if commits are unpushed, say so and ask.

## 3. Ask before assuming

Collect every question that stops the next step from being done without assumptions: leftovers from this session (undecided items, unconfirmed behaviour, anything uncommitted that is not clearly yours) and anything the next step's work order leaves open (read it with `todo_next` / `todo_show` first, without claiming). Ask them all at once with the question tool (AskUserQuestion; one explanation per question, the recommended answer marked), as many as there are, and repeat rounds until nothing is left to assume. Do not continue or launch until the answers are in.

## 4. Decide where the next step runs

- **Room here** (context under about 150k, and the chosen profile's `session` under 80% and `week_all` under 80%): continue in this session. For a plan, `todo_next` on the plan, `todo_claim` the step, follow its work order.
- **Otherwise** launch a continuation. Choose:
  - **Profile:** the account the work belongs to: `work` for the Work area or a repo of the current job, else `personal`. Pass `--profile <name>` only when it differs from this shell's `CLAUDE_CONFIG_DIR`. If that profile's `session` is at 90% or more, do not launch: say when it resets and wait or ask Andres.
  - **Model:** the step's `tier` from the work order: Opus only if it says planning or judging, otherwise Sonnet. No tier: Sonnet, and say so.
  - **Agent:** Claude through `sessioneer` (`--agent` only if Andres asks).
  - **Workdir:** the repo the step names (its `repos` field), else this one.
  - **Effort:** the tier's effort from the model-routing lists: `--effort medium` for Sonnet, `--effort high` for Opus.
  - **Mode:** `--mode auto`.
  - A step that needs a decision (`decision needed`, a push, an Opus tier) is confirmed with Andres before launching.

## 5. The prompt (as small as it can be while complete)

- **Dibs plan:** a few lines, no handoff file:
  `Call todo_next on plan <id>, claim the step it returns (agentName <claude>:<session name>:<conversation id>) and follow its work order. Before starting, ask Andres every question you have, in as many rounds as needed, and assume nothing. Answers already given: <only the decisions from step 3 the work order does not contain>.`
- **No Dibs plan** (small work): one self-contained prompt with the goal, the repo and branch, the decisions made, the files involved, the commands to run, what is out of scope and what to ask first. Everything the new session needs and nothing it can look up itself. Write a handoff (the `handoff` command) only if the state does not fit in the prompt.

Launch: `sessioneer --workdir <dir> --model <m> --effort <level> --mode auto [--profile <p>] "<prompt>"`. Report the session name, profile, model and workdir, and what you asked or answered. Do not keep working on the same step here afterwards. Finish anything still left (answer a peer, record a last checkpoint), confirm no claim is held (`todo_claim_status`), and then say plainly, as the last line: **"Safe to archive this session."** If something is still open (a claim, an unanswered question, uncommitted work that is not yours), say instead what blocks archiving and do not print that line.
