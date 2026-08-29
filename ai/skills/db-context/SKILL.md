---
name: db-context
description: Database context for Laravel projects: MySQL/MariaDB vs SQLite conventions, N+1 query gotchas, and transaction handling. Use when working with DB code, tests, or choosing a DB for a new project.
---

# Database Context

Applies across Laravel projects (OpenCart has its own conventions — see
`opencart-legacy.md`).

## MySQL/MariaDB vs SQLite

- Not a hard rule, but a general pattern: live ecommerce/work projects typically run
  MySQL/MariaDB; personal projects typically run SQLite. Some smaller work projects
  may still use SQLite — it's not exclusively a "personal = SQLite" split.
- Always check the actual project's `.env` / config rather than assuming based on
  project type. When setting up a new project via `/project-bootstrap`, ask which is
  intended if it's not obvious from context.

## Things to watch for

- **N+1 queries** — be deliberate about eager loading (`with()`, `load()`) when
  working with relationships, especially in anything that loops over a collection.
  This is the main recurring trap to watch for.
- No other specific driver-gotchas are flagged at this time (e.g. no known issues with
  enums, JSON columns, or full-text search differences between MySQL and SQLite in
  these projects) — but if a driver-specific quirk comes up, treat it as worth a quick
  check rather than assuming both behave identically.

## Transactions

See `laravel-conventions.md` — actions performing multiple related writes should be
wrapped in a DB transaction, with failures reported clearly rather than silently
swallowed.
