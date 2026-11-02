Audit the public repos and résumé that back my job search, from the perspective of the people
who will actually read them: a recruiter skimming for 30 seconds, a senior engineer opening
the code before an interview, and an outside contributor deciding whether they can help.
It edits no repo, résumé or profile file: it files findings in Dibs and produces a prioritised
report I act on afterwards. The one write it makes is the proposed wording in the two notes files
(see "Notes files").

**Arguments:** $ARGUMENTS

- No argument: audit everything (the five repos + the résumé, profile README and LinkedIn).
- One or more repo names (`insights`, `dibs`, `sessioneer`, `homie`, `dotfiles`): audit only those.
- `resume`: audit only the résumé, profile README and LinkedIn.
- `quick`: skip the per-repo reader-lens deep dives (phase 3), run only phases 0-2 and the
  recruiter/interviewer pass.
- `tools`: also run each project's own test and lint commands (phase 4, see its rules).

The audit has phases, run in order per repo. Repos run in parallel; phases within a repo do not.

| Phase | What | Model |
| --- | --- | --- |
| 0 | Scope and staleness gate | orchestrator |
| 1 | Facts from the atlas | Sonnet |
| 2 | Tool checks (breadth) | Sonnet |
| 3 | Reader-lens checks (independent of the atlas) | Sonnet gathers, Opus judges |
| 4 | Findings and report | Opus |

---


Detail lives in `~/dotfiles/ai/reference/job-search-audit/`; read the file a step names when you
reach it, not before.

## Flow

1. **Phase 0** (`phase0-scope-and-rules.md`): resolve repos from the Dibs atlas parents
   (`todo_list` label `feature atlas`), run the freshness gate (clean tree, local = origin tip,
   compare each subsystem's `verified-at`), look up prior `Job search audit: <date>` and open
   `bug`/`docs drift`/`portfolio` tasks. Read the same file's "Rules every agent must follow"
   before launching any worker and paste them into each worker prompt.
2. **Phases 1-3** (`phases1-3-evidence.md`), per repo in parallel: atlas facts and doc leads, then
   whole-tree read-only scans, then reader-lens checks on a fresh 10-15 file sample (skipped with
   `quick`), then the recruiter/interviewer pass over the résumé, profile README, LinkedIn PDF
   and repos. `resume` runs only the pass over the profile materials.
3. **Phase 4** (`phase4-report.md`): optional `tools` run (ask first), Opus judgement with a
   spot-check of each worker's most severe claim, findings shape, filing only after Andres decides,
   file accounting, notes files, consolidated report with the three-reader verdict.

## Non-negotiables (full text in the reference files)

- No edits in any audited repo or the résumé materials; workers return findings, the orchestrator
  alone writes Dibs; the only writes are the two notes files.
- Every finding cites `file:line` and quotes the text; unverifiable ones go in an "unverified" section.
- Search for shapes (domains, absolute user paths, IPs, emails, key filenames) over the whole tree
  including fixtures, comments and git history; only tracked files count.
- Do not re-flag decided items: the public `ac495.net` apex and contact address, `dotfiles/bin/`
  binaries; exact test or assertion counts in public material are always a finding.
- Launch workers as headless `sessioneer --mode auto` sessions (Agent subagents only when
  `sessioneer` is missing); Sonnet gathers about 300 words each, Opus judges.
- Present decisions in one batch with a recommendation each; fix nothing until Andres picks.
