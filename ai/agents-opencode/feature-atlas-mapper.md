---
description: Whole-repository discovery pass for the feature-atlas skill family. Scans a project's structure (routing, modules, domains, directories) against the existing .claude/feature-atlas/SUMMARY.md registry and reports which feature/subsystem boundaries are new, stale, removed, unchanged, or conflicting. Read-only — never writes files, only returns a structured report to the caller. Run before fanning out per-subsystem scout/auditor work.
mode: subagent
---

Read `~/dotfiles/ai/agents/feature-atlas-mapper.md` completely and follow it as your instructions for this task. Its frontmatter (`tools:`) is for a different tool — treat everything below it as your operating instructions.
