# Backup and restore (Step 23: непрерывность)

## Что уже работает автоматически

- **Перед каждой миграцией**: деплой делает `pg_dump` в `/opt/caos/backup-pre-migration-*.sql` и останавливается, если дамп пуст.
- **Ежедневно в 03:30**: `/etc/cron.d/caos-backup` → `/usr/local/bin/caos-backup.sh` (устанавливаются идемпотентно деплоем из `scripts/caos-backup.*`).
  - Ежедневные копии: `/opt/caos/backups/daily/` — хранятся 14 дней.
  - Еженедельные (воскресенье): `/opt/caos/backups/weekly/` — 56 дней.
  - Лог: `/var/log/caos-backup.log`.

## Восстановление

```bash
# 1. Остановить бэкенд, чтобы он не писал в базу во время восстановления
cd /opt/caos && docker compose -p caos-platform stop backend

# 2. Восстановить дамп (пример: последний ежедневный)
LATEST=$(ls -t /opt/caos/backups/daily/caos-*.sql.gz | head -1)
gunzip -c "$LATEST" | docker compose -p caos-platform exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

# 3. Проверить инварианты (количество целей/решений/участий до инцидента)
docker compose -p caos-platform exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tc "SELECT count(*) FROM goals; SELECT count(*) FROM decisions"'

# 4. Запустить бэкенд
cd /opt/caos && docker compose -p caos-platform start backend
curl -fsS http://127.0.0.1:8000/health
```

## Учебное восстановление (drill)

`scripts/restore-drill.sh` разворачивает последний ежедневный дамп во временную базу `caos_restore_test`, сравнивает инварианты (goals/decisions/parts/results/evidence/users) с живой и удаляет временную. Первый прогон (2026-09-15): **DRILL PASSED**, инварианты совпали. Запуск: `ssh <vps> 'sh -s' < scripts/restore-drill.sh`.

Тот же drill вскрыл переполнение диска (build cache Docker 3.2 GB) — деплой теперь ограничивает кэш (`--keep-storage 1GB`).

## Известное ограничение

Бэкапы лежат на том же сервере, что и база (Step 23 п.5: «backup не рядом с оригиналом»). Следующий шаг по плану непрерывности — off-site копия (rsync на вторую машину tailnet или объектное хранилище) — требует второй площадки, решается на уровне владельца.
