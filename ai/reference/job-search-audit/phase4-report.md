# Phase 4: tool runs, judgement, filing, launching workers, notes files, report

Reference for the `job-search-audit` command; read it at the step the command names.

## Phase 4: findings and report

**Tool runs (only with the `tools` argument).** For each repo, in a detached worktree at the
origin tip (never in a checkout that is a running site), run the project's own documented
test/lint commands the way its CLAUDE.md says (usually inside its test container). The suite must
use an isolated test database, and the run must not take any real-world-visible action; if either
can't be guaranteed, skip that repo and say so. Say what I'm about to run and get my go-ahead
first. Without `tools`, rely on CI results from phase 2.

**Judgement.** The strongest model (Opus) ranks the workers' compact findings and the code
excerpts they cite, not the raw repos. Sonnet tends to grade too kindly; Opus is for catching what
a reader would actually weigh. Before relaying the top findings, spot-check the most severe claim
from each worker against the actual file: workers confidently report things that turn out to be
wrong.

**Findings shape.** One finding, one shape, shared with the atlas audit (`/feature-atlas`,
"Findings"): kind (`bug` | `docs drift` | `portfolio`), repo, atlas subsystem id, Verified-at SHA,
`file:line` with the quoted text, severity, and a suggested fix with options where there's a real
trade-off. Kind rules: a defect in the code is `bug`; a doc that disagrees with the code or atlas
is `docs drift`; anything that affects only how the repo reads to a hiring manager (leaks, tone,
buried stories, hygiene, README polish) is `portfolio`. Unverified items go in a separate
section, not filed.

**Filing.** Findings become ordinary Dibs tasks in the repo's Group, labelled with their kind,
under one `Job search audit: <date>` parent task. `todo_search` for an existing open task first
and update it instead of filing a duplicate. File nothing until I've decided (below): during the
run, workers' findings live in the report. The file-accounting list is kept in the parent task.

**File accounting.** Every report ends with the files actually looked at: each sampled file with
its subsystem id and why it was chosen (always, random, or unread glob), the whole-tree scans that
were run, and what was not read at all. A claim made about code that isn't on that list is
unverified. Calibrate occasionally: run one repo's audit on both models and diff the results; drop
the stronger model from a step where the cheaper one matches, keep it where it finds real issues.

**Launching workers.** Background subagents can hang forever on a permission prompt nobody sees.
When the `sessioneer` CLI is on PATH, launch each worker and the judge as a headless session
instead: `sessioneer --workdir <scratch dir> --model <sonnet|opus> --effort <medium|high> --mode auto "<prompt>"`.
Always pass `--mode auto`. Put the long worker prompt in a file in the scratch dir and make the
launch prompt "read <file> and follow it" plus the per-repo parameters; have each worker write its
report to a file there, and `sessioneer --kill <name>` each session once its report is read. Use
`Agent` subagents only when `sessioneer` is unavailable. Workers use `git -C <path>` and absolute
paths, never `cd` compounds, and keep command output small (count with `-c`/`-l` rather than
printing hundreds of hits).

**Models and other tools.** Evidence gathering (phases 1-3 workers) is mechanical reading and
listing: use a mid-tier model (Sonnet) and have workers return about 300 words each. To save
Claude tokens, evidence gathering may run on Codex, Antigravity's `agy` or opencode instead, at
the model and reasoning level that suits the step (check what is installed and which models are
offered; never guess a name; launch details are in the `orchestrator-worker` skill's cross-tool
section). Outside Claude the no-edit rules are on the worker's honour, so give it the repo path and
the rules in the prompt and verify what comes back. Where one agent would both gather and judge,
split it into those two steps.

**Notes files.** After the report, and only for the résumé and LinkedIn, write the proposed wording
as notes for me to apply by hand (I edit the résumé and LinkedIn myself; the audit never touches
the ODT/PDF or LinkedIn):
- `~/Documents/andres/resume/current/php/resume-review-notes.md`: update the existing file in
  place, keep its structure (agreed direction, section-by-section proposed wording, already
  reflected, still pending, contact details), refresh stale facts and tips, and move items that
  are now done to "already reflected" instead of deleting them.
- `~/Documents/andres/resume/current/php/linkedin-review-notes.md`: same style, created if
  missing: agreed direction, then per LinkedIn section (headline, About, Featured, Experience,
  Skills, other) the current text, the proposed replacement, and why. Include the
  consistency fixes against the résumé and README, and the checklist of what to change by hand.
No exact test or assertion counts in proposed wording. These files hold proposals only, never
secrets, and nothing in them is final until I apply it.

**Report to me.** One consolidated, deduplicated, cross-repo priority list, highest impact first,
each item with why it matters *for the job search specifically*. Group anything that appears in
more than one repo (the same leak pattern, the same doc-drift class) so I fix it once everywhere.
Open with the three-reader verdict (CALL BACK / MAYBE / PASS, with strongest and weakest
reasons, the changes that would raise it, and the overall paragraph). Then the "already strong, don't touch" list and a per-repo release line. Say which items are
purely mechanical and which need a decision from me, present the decisions in one batch with a
recommendation each, and don't start fixing anything until I've picked.
