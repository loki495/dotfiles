# Message templates

Fixed shapes for the messages sessions send each other, so they are parseable and cold-readable.
Rule: every launch, reassignment, peer message and Dibs-bookkeeping request uses these.
Add a new recurring shape here instead of improvising it in a prompt.

## Session name

- First line of every new session's prompt: `Session name: <name>`. When `sessioneer --name` exists, pass `--name "<name>"` too, on creation and on reassignment.
- A worker's name starts with `[worker] ` (`[worker] migrate dns`) so the Sessioneer UI can filter it.
  Orchestrators and review sessions use plain names.
- Reassigning a live session: send `Session name: <new name>` as the first line of the message, and
  update the Dibs claim identity (`<agent>:<new name>:<conversation id>`) so UI and Dibs agree.
- Free-text names use spaces, not hyphens (rule 748).

## Worker launch prompt

Self-contained, about 400 words (rule 926). Keep the existing `[WORKER session=...]` line from
`launching-workers.md` (Worker Session Tagging) directly under the name line.

    Session name: [worker] <task name>
    [WORKER session=<plan id>/<task id> parent=<parent session id>]
    Model/effort: <agent> <model> <effort> (<tier>, <why>)
    Dibs: task <id>, plan <id>. Workdir: <path>. Branch: <branch>.
    Goal: <one sentence>
    Files: <paths you may touch; nothing else>
    Acceptance: <observable checks>
    Return: the result block below, 300 words or less.

## Worker result block

    Status: done | blocked | partial
    Commits: <sha> <subject>, or none
    Tests: <command> -> <pass/fail>, or none: <why>
    Dibs ids touched: <ids>
    Open questions: <list or none>

## Peer message (`sessioneer --send`)

    From: <your session name> (task <id>)
    Ask: <information or request, never approval>
    Why it matters: <one line>
    Reply by: <`--send` back to my name | not needed>

## Dibs bookkeeping request (for the dibs-block hook, rule 1307)

When asking a Claude Code session to record state, give it the block to append, not tool-call steps:

    ```dibs
    claim <id>
    note <id>: <one checkpoint>
    append <id> ## <Section>
      <text>
    done <id> sha=<sha> tests="<command>" docs=<files> :: <summary>
    atlas <subsystem>: <change>
    ```

Codex, opencode and agy have no hook: ask them to use the MCP tools or CLI instead.
