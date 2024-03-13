#!/bin/bash

BASE_PATH="/home/ubuntu/cronjobs/crons"

HOSTS="retrogamingstores.com pandoraplatinum.com localleadfinder.net getfoundengage.com"

set -x

sudo find /var/spool/cron/ -name ".*" -prune -o -type f -print -exec cat {} \; > "$BASE_PATH/backups.cron"

set +x
    
for HOST in $HOSTS; do
    source "/home/ubuntu/backups/$HOST/backup.conf"
    echo "Backing up $HOST..."
    ssh -i $SSH_KEY -p $SSH_PORT $SSH_USER@$SSH_HOST 'sudo find /var/spool/cron/ -name ".*" -prune -o -type f -print -exec cat {} \;' > "$BASE_PATH/$HOST.cron"
    echo "   done..."
done
echo "DONE WITH ALL BACKUPS"
