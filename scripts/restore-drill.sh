#!/bin/sh
# One-off restore drill (Step 23 #17: Test 4 - restore from backup).
set -e
LATEST=$(ls -t /opt/caos/backups/daily/caos-*.sql.gz | head -1)
LIVE_DB=$(grep -E '^POSTGRES_DB=' /opt/caos/.env | head -1 | cut -d= -f2- | tr -d "\"'")
echo "restore drill from: $LATEST"
cd /opt/caos
docker compose -p caos-platform exec -T db sh -c 'psql -U "$POSTGRES_USER" -d postgres -qc "DROP DATABASE IF EXISTS caos_restore_test" -qc "CREATE DATABASE caos_restore_test"'
gunzip -c "$LATEST" | docker compose -p caos-platform exec -T db sh -c 'psql -U "$POSTGRES_USER" -d caos_restore_test -q' 2>&1 | grep -ci error || echo "0 restore errors"

invariants() {
  docker compose -p caos-platform exec -T -e DRILL_DB="$1" db sh -c 'psql -U "$POSTGRES_USER" -d "$DRILL_DB" -tAc "
    SELECT '"'"'goals='"'"' || (SELECT count(*) FROM goals)
        || '"'"' decisions='"'"' || (SELECT count(*) FROM decisions)
        || '"'"' parts='"'"' || (SELECT count(*) FROM goal_participations)
        || '"'"' results='"'"' || (SELECT count(*) FROM results)
        || '"'"' evidence='"'"' || (SELECT count(*) FROM competence_evidence)
        || '"'"' users='"'"' || (SELECT count(*) FROM users)"'
}
LIVE=$(invariants "$LIVE_DB")
REST=$(invariants caos_restore_test)
echo "live:     $LIVE"
echo "restored: $REST"
[ "$LIVE" = "$REST" ] && echo "DRILL PASSED: invariants match" || echo "DRILL FAILED"
docker compose -p caos-platform exec -T db sh -c 'psql -U "$POSTGRES_USER" -d postgres -qc "DROP DATABASE IF EXISTS caos_restore_test"' >/dev/null
echo "temp db dropped"
