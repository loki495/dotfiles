#!/usr/bin/env bash
# Git pre-commit hook for Laravel projects.
# Installed by /project-bootstrap as a symlink at .git/hooks/pre-commit.
# Flow: Pint (fix + restage) → PHPStan (block) → Rector dry-run (block) → Pest (block)
# OpenCart projects: this hook exits immediately (no artisan = not Laravel).
set -euo pipefail

# Must be run from the git root — git does this automatically for hooks
[[ -f "artisan" ]] || exit 0  # not a Laravel project, skip silently

COMPOSE="docker-compose.yml"
if [[ ! -f "$COMPOSE" ]]; then
    echo "pre-commit: no docker-compose.yml found in project root, skipping checks"
    exit 0
fi

CONTAINER=$(grep -o 'container_name: [^[:space:]]*' "$COMPOSE" | grep -v vite | head -1 | awk '{print $2}')
if [[ -z "$CONTAINER" ]]; then
    echo "pre-commit: could not determine container name from docker-compose.yml"
    exit 0
fi

# Get staged PHP files only
STAGED_PHP=$(git diff --cached --name-only --diff-filter=ACM | grep '\.php$' || true)
[[ -n "$STAGED_PHP" ]] || exit 0  # no PHP files staged, nothing to check

# PHPStan analyses per-project configured paths (phpstan.neon), which for a
# typical Laravel project exclude resources/views — Blade-embedded PHP (e.g.
# Livewire single-file components) analysed in isolation, outside that project
# context, produces unreliable type inference. Only give PHPStan plain .php files.
STAGED_PURE_PHP=$(echo "$STAGED_PHP" | grep -v '\.blade\.php$' || true)

echo "=== Pre-commit: Laravel quality checks ==="

# --- 1. Pint (auto-fix and restage) ---
if docker exec "$CONTAINER" test -f ./vendor/bin/pint 2>/dev/null; then
    echo "--- Pint (auto-fix) ---"
    # Pass each file; pint modifies them on the host via the volume mount
    echo "$STAGED_PHP" | xargs docker exec "$CONTAINER" ./vendor/bin/pint 2>&1 || true
    # Restage pint's fixes so they're included in the commit
    echo "$STAGED_PHP" | xargs git add
fi

# --- 2. PHPStan (blocks commit on failure) ---
if [[ -n "$STAGED_PURE_PHP" ]] && docker exec "$CONTAINER" test -f ./vendor/bin/phpstan 2>/dev/null; then
    echo "--- PHPStan ---"
    if ! echo "$STAGED_PURE_PHP" | xargs docker exec "$CONTAINER" ./vendor/bin/phpstan analyse --no-progress; then
        echo ""
        echo "PHPStan errors found. Fix them before committing."
        exit 1
    fi
fi

# --- 3. Rector dry-run (blocks commit if changes would be made) ---
if docker exec "$CONTAINER" test -f ./vendor/bin/rector 2>/dev/null; then
    echo "--- Rector (dry-run) ---"
    if ! docker exec "$CONTAINER" ./vendor/bin/rector process --dry-run --no-progress-bar 2>&1; then
        echo ""
        echo "Rector found suggested changes. Review them (composer rector) and apply"
        echo "before committing. Never auto-apply without reviewing the diff."
        exit 1
    fi
fi

# --- 4. Pest (blocks commit on failure) ---
if docker exec "$CONTAINER" test -f ./vendor/bin/pest 2>/dev/null; then
    echo "--- Pest ---"
    if ! docker exec "$CONTAINER" ./vendor/bin/pest; then
        echo ""
        echo "Tests failed. Fix the underlying code before committing."
        echo "Do not modify or skip tests to force a pass without explicit confirmation."
        exit 1
    fi
fi

echo "=== All pre-commit checks passed ==="
exit 0
