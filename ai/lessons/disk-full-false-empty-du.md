---
topic: disk-full-false-empty-du
tags: [linux, bash, disk, debugging, general]
---

When `df` reports a filesystem full (0 available) but `du -sh <path>/* | sort -rh`
comes back completely empty, don't conclude the directory is actually empty —
two unrelated causes can produce that exact false-empty result:

1. **Shell glob expansion silently hits "Argument list too long"** when the
   directory has thousands of entries (`<path>/*` expands before `du` even runs).
   Fix: run `du` on the directory itself with `--max-depth=N` instead of
   glob-expanding its contents — `du -h --max-depth=1 <path> 2>&1 | sort -rh`
   recurses via `readdir` internally and never hits the shell's argument limit.

2. **A still-running process holds open file handles to already-deleted
   (unlinked) files.** The space stays consumed until that process exits or
   closes the handle, but no directory listing (`ls`, `find`, `du` on the real
   path) will ever show it, since the file has no remaining directory entry.
   Find these with `lsof +L1 2>/dev/null` (lists open files with a zero link
   count) — filter to the mountpoint in question (e.g. `| grep /tmp`) since the
   full output is typically large and mostly irrelevant.

Confirmed 2026-09-02: a 7.8G tmpfs `/tmp` reported 100% full; `du -sh /tmp/*`
returned nothing (cause 1 — thousands of leftover small directories from past
test runs made the glob too large); `lsof +L1 | grep /tmp` returned real but
small results (~70MB of deleted browser temp files — cause 2, present but not
the actual driver). The real 5.7G cause only showed up once `du --max-depth=1`
was used directly on the directory: a single large, completely unrelated
orphaned directory that neither cause-1 nor cause-2 diagnosis would have
surfaced on its own. Lesson: when the "obvious" recent-activity suspects don't
add up to the reported usage, run the plain `--max-depth` scan before
concluding anything about the cause — don't stop at the first plausible
explanation that fits recent events.
