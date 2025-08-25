#!/usr/bin/env bash
# import-sql.sh
# Usage:
#   ./import-sql.sh --clear
#   ./import-sql.sh myfile.sql.gz
#   ./import-sql.sh --all
#   ./import-sql.sh --all --ignore-multi "pattern1" "pattern2"
#   ./import-sql.sh --all --ignore-single "pattern"
#   ./import-sql.sh --dry-run ...

DB_CONTAINER="retrogamingstores-db"
DB_USER="user"
DB_PASS="pass"
DB_NAME="app"
DRY_RUN=false

usage() {
  echo "Usage:"
  echo "  $0 --clear                    # remove all tables"
  echo "  $0 <file.sql.gz>               # import single file"
  echo "  $0 --all [--ignore-multi ...] [--ignore-single ...]  # import all files"
  echo "  $0 --dry-run                  # dry run"
  exit 1
}

# Parse arguments
MODE="none"
IGNORE_MULTI=()
IGNORE_SINGLE=""
FILES=()

while [[ $# -gt 0 ]]; do
  case $1 in
    --clear)
      MODE="clear"
      shift
      ;;
    --all)
      MODE="all"
      shift
      ;;
    --ignore-multi)
      shift
      while [[ $# -gt 0 ]] && [[ ! $1 =~ ^-- ]]; do
        IGNORE_MULTI+=("$1")
        shift
      done
      ;;
    --ignore-single)
      shift
      IGNORE_SINGLE="$1"
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -*)
      usage
      ;;
    *)
      FILES+=("$1")
      shift
      ;;
  esac
done

run_mysql() {
  local sql="$1"
  if $DRY_RUN; then
    echo "[DRY RUN] mysql command: $sql"
  else
    docker exec -i "$DB_CONTAINER" mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "$sql"
  fi
}

clear_db() {
  echo "Clearing database $DB_NAME..."
  # get all tables
  local tables
  tables=$(docker exec -i "$DB_CONTAINER" mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -Nse 'SHOW TABLES')
  if [[ -z "$tables" ]]; then
    echo "No tables found."
    return
  fi
  for t in $tables; do
    run_mysql "DROP TABLE $t;"
  done
  echo "Database cleared."
}

import_file() {
  local f="$1"
  echo "Importing $f..."
  if $DRY_RUN; then
    echo "[DRY RUN] gunzip < $f | docker exec -i $DB_CONTAINER mysql -u$DB_USER -p$DB_PASS $DB_NAME"
  else
    gunzip < "$f" | docker exec -i "$DB_CONTAINER" mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME"
  fi
}

# Main logic
case $MODE in
  clear)
    clear_db
    ;;
  none)
    if [[ ${#FILES[@]} -eq 1 ]]; then
      import_file "${FILES[0]}"
    else
      usage
    fi
    ;;
  all)
    for f in *.sql.gz; do
      echo "-------"

      if [[ -n "$IGNORE_SINGLE" ]]; then
        if [[ "$f" =~ $IGNORE_SINGLE ]]; then
          echo "Skipping $f due to single-ignore pattern '$IGNORE_SINGLE' (last - found match) ($IGNORE_SINGLE)"
          unset IGNORE_SINGLE
          continue
        fi
        echo "Skipping $f due to single-ignore pattern '$IGNORE_SINGLE'"
        continue
      fi

      # skip if matches multi-ignore patterns
      skip=false
      for pattern in "${IGNORE_MULTI[@]}"; do
        if [[ "$f" =~ $pattern ]]; then
          echo "Skipping $f due to multi-ignore pattern '$pattern'"
          skip=true
          break
        fi
      done
      if $skip; then continue; fi

      import_file "$f"
    done
    ;;
  *)
    usage
    ;;
esac
