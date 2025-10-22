#!/usr/bin/env bash
##sudo pacman -S python-pipx
##pipx ensurepath
# Install sqlite3-to-mysql
##pipx install sqlite3-to-mysql
# Now you can run:
##sqlite3mysql --help

set -euo pipefail

MYSQL_USER="root"
MYSQL_PASS="rootpassword"
MYSQL_DB="MyVideos121"
MYSQL_HOST="192.168.1.145"
MYSQL_PORT="3307"

TMP_DIR="./kodi_db_tmp"

# Create temporary folder
mkdir -p "$TMP_DIR"
cd "$TMP_DIR"

# Remove any leftover DBs
rm -f ./*.db

# Pull all .db files from Kodi on Shield
adb shell "ls /sdcard/Android/data/org.xbmc.kodi/files/.kodi/userdata/Database/MyVideos*.db" | xargs -n1 adb pull

../update-db.py --sqlite ~/www/kodi-db/$TMP_DIR/MyVideos131.db   --mysql-host $MYSQL_HOST   --mysql-port $MYSQL_PORT   --mysql-user $MYSQL_USER   --mysql-pass $MYSQL_PASS   --mysql-db $MYSQL_DB

# Cleanup
rm -f ./*.db
cd ..
rmdir "$TMP_DIR"
echo "Done."
