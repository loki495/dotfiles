# Token efficiency, git, review, testing, privacy, scope, final completion

Reference for the `orchestrator-worker` skill; read it when the decision tree in `SKILL.md` points here.

## Token Efficiency Practices

These apply to every plan, light or fully delegated — they're what makes file-based
state actually cheaper than re-explaining things in conversation, not just
differently organized:

- **Verify via diffs/status, not full re-reads.** After an edit, don't re-read the
  whole file to confirm it worked — a tool that errors on failure already proves it
  didn't silently fail. Use `git diff`/`git status` for a summary of what actually
  changed, not `cat` of the full file.
- **Prefer targeted search over full reads.** `grep`/glob for a symbol or pattern
  before reading a whole file just to check whether something exists in it.
- **Run checks with quiet/concise output**, and keep only pass/fail + errors in
  `todo_comment` checkpoints — never paste raw verbose CI-style output (full
  test-runner logs, progress bars, full lint dumps) into one. If a tool has a
  terser mode (compact test output, a trimmed static-analysis formatter), use it;
  either way, summarize before posting a checkpoint.
- **Batch independent steps.** Tool calls whose inputs don't depend on each other's
  output belong in the same turn, not sequential round trips — this applies inside
  plan work exactly as it does everywhere else.
- **`/clear` (or a fresh session) between unrelated phases is safe and encouraged**
  once the current phase's state is actually persisted to Dibs — that's the entire
  point of resuming cold from there. Don't carry a large, no-longer-needed
  exploration context into an unrelated next phase just because the session happens
  to still be open.
- **Push deterministic checks to scripts/tools that return pass/fail + errors**, not
  narrated tool output — a lint/type-check/test run belongs in a `todo_comment` as
  "passed" or "3 failures: <what>", not as a transcript of the run.

## Git

Use git to keep a clear record of implementation changes. Before delegating,
establish the project repository and inspect its initial state. After each worker
iteration: `git status`, `git diff`, `git log` — review for unrelated modifications.
Workers may commit when appropriate, but a commit doesn't eliminate the need for
orchestrator review. Never reset, discard, or overwrite user work without explicit
justification.

## Code Review

The orchestrator independently reviews every worker result for: correctness,
requirements compliance, security, privacy, error handling, edge cases,
maintainability, performance, portability, test coverage, and accidental unrelated
changes — pay particular attention to assumptions about external data. If the
implementation is incorrect: document the issue as a `todo_comment` on the task
issue (or `todo_create` a new task under the plan if it's genuinely separate work),
launch the worker again with that context. Don't just say "fix it" without defining
what's wrong.

## Testing

Run tests after meaningful implementation steps. Don't accept "tests pass" without
knowing what was actually tested — see this machine's global sad-path-coverage rule,
which applies here too. Where external/user data is involved: use fixtures for
automated tests, avoid requiring private user data for normal test runs, keep real
user data read-only, and never embed sensitive data into the repository.

## Privacy

Do not unnecessarily copy, persist, print, or commit user prompts, source code,
credentials, API keys, tokens, personal information, or private project data. Process
metadata rather than storing underlying content when only metadata is required.
Review logs/debugging output for accidental sensitive information before they
persist anywhere.

## Scope Control

Don't expand the project because an interesting improvement surfaced mid-task.
Separate required functionality from useful-but-deferred functionality from unrelated
ideas; record deferred improvements if they're likely to matter later; keep the
current implementation focused.

## Final Completion

A plan is complete only when:

1. All required plan tasks are `done`.
2. Acceptance criteria are satisfied.
3. Tests/checks pass.
4. The orchestrator has independently reviewed the implementation.
5. No known critical blockers remain.
6. The working tree contains only intentional changes.
7. Important limitations are documented.
8. The plan issue itself is closed (`todo_complete`/`todo_revise` to final state)
   once the user confirms it's genuinely finished — not just paused. No separate
   archiving step: a closed issue already reads as done, per
   [Completion](plans-and-state.md#completion).

The final report summarizes what was built, important architectural decisions, how
it was verified, known limitations, and relevant future improvements. Don't claim
functionality that wasn't actually verified.
