---
name: session-flow
description: The one state machine for continuing, parking, rotating and cleaning up sessions, with the thresholds file, how to choose the receiving agent, how to ask and how to clear spawned sessions. Use at every step boundary, near quota or a big context, before launching or replacing a session, and before a final status line.
---

# Session flow

One decision for "continue here or somewhere else". Numbers live only in `thresholds.conf` in this
directory: read it, do not restate them elsewhere. Rules: 728 (the state table), 930 (questions),
1226 (status line), and the spawned-session cleanup rule.

## Inputs

- Context size in tokens (status line or transcript) and minutes idle (cache warm or cold).
- `sessioneer --usage`: `session` and `week_all` percent and reset time, per agent and Claude profile
  (`personal` is `~/.claude`, `work` is `~/.claude-work`).
- Whether work waits on Andres or another session, and whether a plan has more steps.

## States

| State | When | Do |
| --- | --- | --- |
| GO | Context and quota under the GO limits, cache warm | Continue here. |
| WARM TIGHT | Context or quota between the GO and park/rotate limits | Finish the current step, then CHECKPOINT. Start no large step. |
| CHECKPOINT | A step ends in WARM TIGHT, or before any leaving | Write the checkpoint, update the plan and records, release claims. |
| PARK | Quota at the park limit or more and no other agent or profile has room | File the handoff, release, say when quota resets. Offer a scheduled wake-up (`at`) only when the job exists; phase 3 adds it. |
| ROTATE | A trigger fired (context at the rotate limit, cold cache with big context, quota) and another agent or profile has room | File the handoff, launch the receiver, archive this session once the receiver has claimed it. |
| WAIT | Waiting on Andres or another session | Status line only; the claim may stay. |
| DONE | The plan or request is finished | Closer checks, clear spawned sessions, then "Safe to archive" or "All planned work is done". |

Output of a decision: state, why, agent, model, effort, profile, workdir, prompt, needs approval,
reset times. Say it in two lines before acting.

## Questions

Every question, and every proposal to continue in a new session, goes through the agent's question
tool (Claude: AskUserQuestion; in Sessioneer it appears as a prompt band), one decision per question,
recommended option first. Never leave "waiting for you to pick" as plain text. Only an agent with no
question tool uses a numbered list at the end of the reply.

Collect questions before the handoff when quota is under `QUOTA_CARRY`. Answers already given go in
the handoff under Decisions made. At or above `QUOTA_CARRY`, carry the open ones under Open questions
and the receiver asks them. The receiver asks only what Decisions made does not cover.

## Choose the receiver

Used by ROTATE, `/next`, `/handoff` and `/orchestrate`.

- **Agent and model:** the highest-ranked entry that fits the work in `orchestrator-worker`,
  `model-routing.md` ("Model routing by work type"), installed, listing the model, and with quota
  room. Rank order is a preference: pick a lower entry when it fits better or spreads load. Skip an
  agent or profile at `QUOTA_PARK` or more. Frontier, or an advanced tier that only plans or judges,
  needs Andres's approval.
- **Profile (Claude only):** the account the work belongs to, `work` for the Work area or a repo of
  the current job, else `personal`. Pass `--profile` only when it differs from this shell's
  `CLAUDE_CONFIG_DIR`.
- **Effort:** the tier's effort. **Mode:** `--mode auto` (Codex takes `plan` or `full`). **Workdir:**
  the repo the step names, else this one.
- Pushes, real-world actions and frontier tiers still need Andres's approval before launching.

## Handoff and prompt

- Plan with more steps: no handoff file. Prompt: `Call todo_next on plan <id>, claim the step it
  returns (agentName <agent>:<session name>:<conversation id>) and follow its work order. Answers
  already given: <only what the work order lacks>.`
- Anything parked or half done: a temporary handoff task (`session-handoff`, which owns the template)
  and a prompt that names its id and tells the receiver to verify the claims are free and this
  session is archived before working.
- Small work with nothing to carry: one self-contained prompt with goal, repo, branch, decisions,
  files, commands, out of scope.
- The handoff holds Goal, Decisions made, State, Next steps and Don't, not narrative or the old
  session's claims about its own work. The receiver re-verifies State with commands (git, tests,
  Dibs) and does not trust the description. Substantial work keeps the rule 1468 personas, with a
  different agent or model verifying where possible.
- Launch: `sessioneer --workdir <dir> --model <m> --effort <level> --mode auto [--profile <p>]
  --set-name "<name>" "<prompt>"`, `--agent codex` for Codex. Report session name, agent, model,
  effort, profile and workdir. Do not keep working on the same step afterwards.

## Clear what you spawned

Before "Safe to archive this session." or "All planned work is done.", archive every session or worker
this session launched: idle, claim-free ones with `sessioneer --kill <name or conversation id>` (add
`--agent <agent>`; no `--force` on a working or blocked one). Record each launch (name and
conversation id) in the task checkpoint at launch, because `--list` does not yet show who spawned
a session. A session that is still working is not archived; the status is then Waiting on other work.
A session you replaced counts too. Never archive another agent's session.

## Sessioneer commands every agent should know

`sessioneer --usage`, `--whoami`, `--peers`, `--list [--json]`, `--show TARGET`, `--send TARGET "msg"`,
`--kill TARGET`, `--advise [SESSION] [--json]`, and the launch form above. Read `peer-sessions` before
messaging another session.
