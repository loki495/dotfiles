#!/usr/bin/env bash
# Fires after Claude writes or edits a file (PostToolUse hook).
# Runs Pint (auto-fix) then PHPStan (report only) for PHP files in Laravel projects.
set -euo pipefail

PAYLOAD=$(cat)
FILE_PATH=$(echo "$PAYLOAD" | jq -r '.tool_input.file_path // empty')

# Only act on PHP files
[[ "$FILE_PATH" == *.php ]] || exit 0

# Walk up from the file to find the Laravel project root (directory with artisan)
PROJECT_ROOT=""
DIR=$(dirname "$FILE_PATH")
while [[ "$DIR" != "/" && "$DIR" != "." ]]; do
    if [[ -f "$DIR/artisan" ]]; then
        PROJECT_ROOT="$DIR"
        break
    fi
    DIR=$(dirname "$DIR")
done

[[ -n "$PROJECT_ROOT" ]] || exit 0  # not a Laravel project

COMPOSE="$PROJECT_ROOT/docker-compose.yml"
[[ -f "$COMPOSE" ]] || exit 0

# Get the app container name (first container_name that isn't a vite container)
CONTAINER=$(grep -o 'container_name: [^[:space:]]*' "$COMPOSE" | grep -v vite | head -1 | awk '{print $2}')
[[ -n "$CONTAINER" ]] || exit 0

# Relative path inside the container (container root = project root)
REL_PATH="${FILE_PATH#$PROJECT_ROOT/}"

# --- Pint (auto-fix, always succeeds) ---
if docker exec "$CONTAINER" test -f ./vendor/bin/pint 2>/dev/null; then
    echo "==> Pint: $REL_PATH"
    docker exec "$CONTAINER" ./vendor/bin/pint "$REL_PATH" 2>&1 || true
fi

# --- PHPStan (report only — don't block on write, block at commit) ---
if docker exec "$CONTAINER" test -f ./vendor/bin/phpstan 2>/dev/null; then
    echo "==> PHPStan: $REL_PATH"
    docker exec "$CONTAINER" ./vendor/bin/phpstan analyse "$REL_PATH" --no-progress 2>&1 || true
    echo "(PHPStan errors must be addressed before committing)"
fi

exit 0
