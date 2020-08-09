#!/bin/bash

DIRNAME="${0%/*}"
source $DIRNAME/common

usage() {
    echo "Usage:"
    echo "      clone-site [<conf-path>] <sql_path> <code_path>}"
}

if [ $# -lt 3 ]
then
    usage
    exit
fi

if [[ "$1" == *.conf ]]
then
    SQL_PATH=`realpath $2`
    CODE_PATH=`realpath $3`
else
    SQL_PATH=`realpath $1`
    CODE_PATH=`realpath $2`
fi

echo

process_local_code() {
    rm -rf "./$LOCAL_PATH"

    LOCAL_CODE_PATH="${LOCAL_BASE}/${LOCAL_PATH}"
    echo_info "CODE PATH: $CODE_PATH"
    echo_info "LOCAL CODE PATH: $LOCAL_CODE_PATH"
    mkdir -p $LOCAL_CODE_PATH

    TOTAL_FILES=`find $CODE_PATH | wc -l`
    echo "Total files to copy: $TOTAL_FILES"

    echo "Copying files locally"
    rsync -vauhr $CODE_PATH $LOCAL_BASE | pv -qlep -s $TOTAL_FILES > /dev/null
    echo "done"

    echo

    if [[ $SITE_TYPE == 'wordpress' ]]
    then
        echo "Fixing WordPress wp-config.php"
        sed -i "/DB_NAME/s/$OLD_DB_NAME/$MYSQL_DATABASE/g" $LOCAL_CODE_PATH/wp-config.php
        sed -i "/DB_USER/s/,\s*'.*'/, '$MYSQL_USER'/g" $LOCAL_CODE_PATH/wp-config.php
        sed -i "/DB_PASSWORD/s/,\s*'.*'/, '$MYSQL_PASSWORD'/g" $LOCAL_CODE_PATH/wp-config.php
        echo "Done fixing"
    fi
}

process_local_sql() {
    rm -f "./${TMP_SQL_NAME}"
    rm -f "./${MYSQL_DATABASE}.sql.gz"

    OLD_DB_NAME=`basename $SQL_PATH | awk -F '.' '{ print $1}'`

    echo_info "OLD DB NAME: $OLD_DB_NAME"
    LOCAL_SQL_PATH="${LOCAL_BASE}/${MYSQLDUMP_FILE}"
    echo_info "SQL PATH: $SQL_PATH"
    echo_info "LOCAL SQL PATH: $LOCAL_SQL_PATH"

    echo "Copying sql locally"
    rsync -vauhr $SQL_PATH $LOCAL_BASE 2>&1 > /dev/null
    echo "done"

    echo

    SQL_PATH_BASENAME=`basename $SQL_PATH`
    TMP_SQL_NAME=$LOCAL_BASE/$SQL_PATH_BASENAME

    if [[ "$TMP_SQL_NAME" == *.sql.gz ]]
    then
        gunzip $TMP_SQL_NAME
        TMP_SQL_NAME=${TMP_SQL_NAME::-3}
    fi

    sed -i "s/Database\: $OLD_DB_NAME/Database: $MYSQL_DATABASE/g" $TMP_SQL_NAME
    sed -i "s/\`$OLD_DB_NAME\`/\`$MYSQL_DATABASE\`/g" $TMP_SQL_NAME

    mv $TMP_SQL_NAME $MYSQL_DATABASE.sql
    gzip -9 $MYSQL_DATABASE.sql

    echo "Database SQL file fixed and renamed"
}

upload_and_process_sql() {
    echo "Uploading sql file"
    rsync -e "ssh -p $SSH_PORT" -vazuhr $MYSQL_DATABASE.sql.gz $SSH_USER@$SSH_HOST:tmp
    LAST_RESULT=$?

    if [ $LAST_RESULT -gt 0 ]
    then
        echo_error "Error rsync-ing"
        perror $LAST_RESULT
        exit 1
    else
        echo_success "done"
    fi

    run_ssh "cd tmp && gunzip -f $MYSQL_DATABASE.sql.gz && mysql < $MYSQL_DATABASE.sql"
    run_ssh "rm tmp/$MYSQL_DATABASE.sql"
    echo "Done processing sql"

    if [[ $SITE_TYPE == 'wordpress' ]]
    then
        if [[ $SITE_HTTPS -gt 0 ]]
        then
            SITE_URL="https://$SITE_DOMAIN"
        else
            SITE_URL="http://$SITE_DOMAIN"
        fi
        run_ssh_silent "mysql $MYSQL_DATABASE -e \"UPDATE $WP_OPTION_TABLE SET option_value='$SITE_URL' WHERE option_name='siteurl'\""
        run_ssh_silent "mysql $MYSQL_DATABASE -e \"UPDATE $WP_OPTION_TABLE SET option_value='$SITE_URL' WHERE option_name='home'\""

        echo "Done fixing url in WordPress tables"
    fi
}

upload_code() {
    echo "Starting code upload"
    rsync -e "ssh -p $SSH_PORT" -vazuhr --progress $LOCAL_CODE_PATH $SSH_USER@$SSH_HOST:$SSH_BASE_PATH
}

process_post_sql() {
    for sql in "${POST_SQL[@]}"
    do
        run_ssh_silent "mysql $MYSQL_DATABASE -e \"$sql\""
    done
}

process_post_cmd() {
    for cmd in "${POST_COMMANDS[@]}"
    do
        run_ssh_silent "$cmd"
    done
}

process_local_sql
process_local_code
check_mycnf
upload_and_process_sql
upload_code
process_post_sql
process_post_cmd

echo_success "DONE CLONING"
