# Atlas at merge

Reference for the `git-workflow` skill (rule 733).

A session that changes an atlas subsystem does not refresh or stamp the atlas. At the commit or
merge it writes one `atlas <subsystem>: <change>` line per touched subsystem in its dibs block
(Claude Code), or appends the line under `## Pending since last refresh` on the atlas parent
(other agents). The hint queue and that section are maintained by `ai/scripts/atlas-refresh.py`.

A git post-merge hook (`atlas-refresh.py install-hooks` adds it to every atlas repo) queues the
repo; a headless Sonnet `/feature-atlas-subsystem` session per stale subsystem then refreshes it,
immediately when the Claude 5h quota is at most 70%, otherwise in the 03:50 nightly batch.

Reading an atlas whose Verified at is behind the code: `git log --stat <stamp>..HEAD --
<owned_paths>`, trust the code over the comment, read the Pending hints for that subsystem. Never
push, open a PR or merge on account of a stale atlas. The push guard only mentions staleness in its
confirmation prompt; the commit gate reminds you which subsystems a commit touches and refuses a
false `Docs: updated` line.
