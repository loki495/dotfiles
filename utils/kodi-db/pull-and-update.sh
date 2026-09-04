#!/usr/bin/env bash
##sudo pacman -S python-pipx
##pipx ensurepath
# Install sqlite3-to-mysql
##pipx install sqlite3-to-mysql
# Now you can run:
##sqlite3mysql --help

set -euo pipefail

DIRNAME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=/dev/null
source "$DIRNAME/.env" 2>/dev/null || {
    echo "pull-and-update.sh: missing $DIRNAME/.env" >&2
    echo "Copy .env.example to .env and fill it in." >&2
    exit 1
}

# Connects as root because the sync rewrites rows the unprivileged kodi user
# does not own.
MYSQL_USER="root"
MYSQL_PASS="$MYSQL_ROOT_PASSWORD"
MYSQL_DB="$KODI_SYNC_DB"
MYSQL_HOST="$KODI_DB_HOST"
MYSQL_PORT="${MYSQL_PORT:-3307}"

TMP_DIR="./kodi_db_tmp"

# Create temporary folder
mkdir -p "$TMP_DIR"
cd "$TMP_DIR"

# Remove any leftover DBs
rm -f ./*.db

# Pull all .db files from Kodi on Shield
adb shell "ls /sdcard/Android/data/org.xbmc.kodi/files/.kodi/userdata/Database/MyVideos*.db" | xargs -n1 adb pull

"$DIRNAME/update-db.py" --sqlite ./MyVideos131.db   --mysql-host $MYSQL_HOST   --mysql-port $MYSQL_PORT   --mysql-user $MYSQL_USER   --mysql-pass $MYSQL_PASS   --mysql-db $MYSQL_DB

# Cleanup
rm -f ./*.db
cd ..
rmdir "$TMP_DIR"
echo "Done."
