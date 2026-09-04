#!/bin/bash

DIRNAME="${0%/*}"
source "$DIRNAME/backup-tools.conf" 2>/dev/null || {
    echo "backup_crons.sh: missing $DIRNAME/backup-tools.conf" >&2
    echo "Copy backup-tools.conf.example to backup-tools.conf and fill it in." >&2
    exit 1
}

BASE_PATH="$CRON_BACKUP_PATH"

set -x

sudo find /var/spool/cron/ -name ".*" -prune -o -type f -print -exec cat {} \; > "$BASE_PATH/backups.cron"

set +x

for HOST in $BACKUP_CRON_HOSTS; do
    source "$BACKUP_BASE_PATH/$HOST/backup.conf"
    echo "Backing up $HOST..."
    ssh -i $SSH_KEY -p $SSH_PORT $SSH_USER@$SSH_HOST 'sudo find /var/spool/cron/ -name ".*" -prune -o -type f -print -exec cat {} \;' > "$BASE_PATH/$HOST.cron"
    echo "   done..."
done
echo "DONE WITH ALL BACKUPS"
