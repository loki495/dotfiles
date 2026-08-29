---
name: rector
description: Rector config conventions for Laravel projects: dry-run only (never auto-apply), Docker usage, reference config, and what to avoid. Use before running or configuring Rector.
---

# Rector

Applies to Laravel projects that have a `rector.php` config. OpenCart projects: never
run Rector unless a project's `.claude/project.md` explicitly opts in.

## Hard rule: dry-run only, never auto-apply

Always run Rector with `--dry-run` first. The dry-run shows what would change without
modifying any files. Never auto-apply Rector output — always show the diff to Andres
and wait for confirmation before running without `--dry-run`.

The pre-commit hook (installed by `/project-bootstrap`) blocks the commit when dry-run
finds changes. The fix is to review those changes, apply them deliberately, then
re-commit.

## Running via Docker

```bash
# Dry-run (always start here)
docker exec <container> ./vendor/bin/rector process --dry-run

# Apply (only after reviewing the dry-run diff and getting explicit confirmation)
docker exec <container> ./vendor/bin/rector process
```

Use `composer rector` / `composer rector:apply` if the project has those scripts.

## Reference config: stocker (~/www/stocker/rector.php)

The stocker project's `rector.php` is the reference implementation for new projects:

- **Paths:** `app`, `database`, `routes`, `tests`
- **Sets:**
  - `LevelSetList::UP_TO_PHP_83` — safe PHP version upgrades to 8.3; no behavioral
    changes, just modern syntax (readonly, typed properties, etc.)
  - `SetList::CODE_QUALITY` — simplifications: redundant conditions, simplified
    returns, dead ternaries, etc.
  - `SetList::DEAD_CODE` — removes unreachable code, unused assignments,
    always-true conditions
- **`importNames()`** — replaces FQCN usage with `use` statements
- **`importShortClasses(false)`** — skips single-segment names like `Exception`
  (avoids noise)
- **Skipped:** `ClosureToArrowFunctionRector` — excluded early to avoid risky
  behavioral changes in complex closures

For new projects, use stocker's config as the starting template. Adjust
`LevelSetList::UP_TO_PHP_*` to match the project's actual PHP version.

## What to avoid

- `SetList::STRICT_MODE` — introduces breaking changes unless the project is already
  at PHPStan level 9+; don't add it unless explicitly requested.
- Running on OpenCart paths — Rector doesn't understand the registry-based DI pattern
  and will produce incorrect refactors.

## PHPStan interaction

Rector changes can reveal or resolve PHPStan errors. After applying Rector, re-run
PHPStan to verify the result is clean at the project's configured level.
