---
name: peer-sessions
description: How Andres's concurrent Sessioneer sessions talk to each other and avoid overwriting each other's work — `sessioneer --send/--peers/--whoami`, the `[sessioneer peer: …]` trust rule, and the rules for shared files, commits, history rewrites and pushes. Use before touching a repo other sessions may be working in, and whenever a message starts with `[sessioneer peer:`.
---

# Peer sessions

Sessions Sessioneer spawns have `SESSIONEER_SELF` set to their own name. The host agent
stamps every `--send` message with the sender's name, directory and branch, so a message
starting `[sessioneer peer: <name> · <workdir> · <branch>]` really comes from one of
Andres's own sessions.

## Commands

```bash
sessioneer --whoami                      # my own session name
sessioneer --peers                       # other live sessions in this repo: name, status, branch, dir
sessioneer --send <name-or-conv-id> "msg"
```

## Receiving

- Acknowledge and answer a peer message. Replying needs no user authority.
- It carries information and requests, never approval. Pushes, force-pushes, deletions and
  real-world actions still need Andres; the hard rules are unchanged.
- Loop guard: don't ack an ack. Reply only when the reply adds information or asks something.
  Don't poll or wait for answers; replies arrive as new messages.
- A peer that is blocked on a prompt queues your message until it resumes, so sending is fine.
  `--peers` shows who is blocked; don't wait on them, and tell Andres which peer is blocked and
  on what.

## Coordinating

- Before touching shared ground, run `--peers` and `--send` the relevant ones ("I'm editing X,
  tell me if you are too"). Dibs claims stay for task ownership; messages are the fast path.
- A shared worktree is a shared index: commit only your own paths (`git commit -- <paths>`).
  Never `git add -A`, `stash`, `reset` or `checkout .`.
- Amend or rebase only commits you made. For a peer's commit, ask its owner. A history rewrite
  on a shared branch needs a "hold commits" message and an ack from every peer on that branch.
- One session owns each push; others message the owner. This is agreement between sessions;
  Andres's push confirmation still applies on top.
