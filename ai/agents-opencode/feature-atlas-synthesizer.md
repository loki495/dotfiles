---
description: Cross-subsystem validation and synthesis for the feature-atlas skill family. Reads every subsystem's DETAILS.md and AUDIT.md, independently re-verifies findings, rejects/narrows/demotes weak ones, runs coverage/duplication/DRY/over-abstraction/schema-completeness/dependency-ranking meta-passes, and writes the final REPORT.md and SUMMARY.md digest. Read-mostly — writes only REPORT.md (and the SUMMARY.md descriptive digest section).
mode: subagent
---

Read `~/dotfiles/ai/agents/feature-atlas-synthesizer.md` completely and follow it as your instructions for this task. Its frontmatter (`tools:`) is for a different tool — treat everything below it as your operating instructions.
