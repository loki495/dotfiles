---
description: Whole-repository discovery pass for the feature-atlas skill family. Reads the project's Format v2 atlas (Dibs parent issue + subsystem comments, or .ai/feature-atlas/ files when Dibs is unreachable), runs the Refresh procedure (per-comment pathspec diff, coverage diff, removals), proposes boundaries on a first run, and reports which subsystems are new, stale, removed, unchanged, or conflicting. Read-only — never writes files or Dibs items, only returns a structured report to the caller. Run before per-subsystem scout work.
mode: subagent
---

Read `~/dotfiles/ai/agents/feature-atlas-mapper.md` completely and follow it as your instructions for this task. Its frontmatter (`tools:`) is for a different tool — treat everything below it as your operating instructions.
