#!/bin/sh
# Daily database backup for CAOS (critique part two, Step 23).
# Installed idempotently by .github/workflows/deploy.yml as
# /usr/local/bin/caos-backup.sh; scheduled via /etc/cron.d/caos-backup.
# Retention: 14 daily, 8 weekly (Sundays).
set -e
STAMP=$(date +%Y%m%d_%H%M%S)
DIR=/opt/caos/backups
mkdir -p "$DIR/daily" "$DIR/weekly"
cd /opt/caos
docker compose -p caos-platform exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  > "$DIR/daily/caos-$STAMP.sql.tmp"
gzip -f "$DIR/daily/caos-$STAMP.sql.tmp"
mv "$DIR/daily/caos-$STAMP.sql.tmp.gz" "$DIR/daily/caos-$STAMP.sql.gz"
test -s "$DIR/daily/caos-$STAMP.sql.gz"
DOW=$(date +%u)
[ "$DOW" = "7" ] && cp "$DIR/daily/caos-$STAMP.sql.gz" "$DIR/weekly/caos-week-$STAMP.sql.gz"
find "$DIR/daily" -name 'caos-*.sql.gz' -mtime +14 -delete
find "$DIR/weekly" -name 'caos-*.sql.gz' -mtime +56 -delete
