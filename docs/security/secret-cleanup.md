# Ротация секретов и чистка git-истории

Статус: **требует действий владельца**. Файлы с секретами удалены из HEAD, но секреты остаются в истории git и считаются скомпрометированными.

## 1. Ротация (сделать немедленно, до чистки истории)

| Секрет | Где был | Что сделать |
|---|---|---|
| Stepik OAuth client secret | `setup_stepik_env.sh` (в git с коммита `43ed94e`) | Перевыпустить секрет в кабинете Stepik; обновить `/opt/caos/.env` |
| Google OAuth client secret | `setup_google_env.sh` (локально) | Перевыпустить в Google Cloud Console; обновить `/opt/caos/.env` |
| OpenRouter API key | `test_llm.sh` (локально) | Отозвать ключ, создать новый; обновить `AI_API_KEY` |
| FTP-пароль TimeWeb (пользователь `windsurf`) | `check_index.sh`, `deploy_frontend.sh` (в git с `e1898d0`) | Сменить пароль в панели TimeWeb; обновить `FTP_PASS` в GitHub Secrets |

Обновлённые значения: на VPS — `/opt/caos/.env`, в CI — Settings → Secrets and variables → Actions.

## 2. Чистка git-истории (после ротации)

Секреты остались в коммитах `43ed94e` и `e1898d0`. Порядок:

```bash
pip install git-filter-repo
cd <клон>
git filter-repo --invert-paths --path setup_stepik_env.sh \
  --path check_index.sh --path deploy_frontend.sh --path create_thinkred_chain.py
git remote add origin git@github.com:thethinkred-ai/caos-platform.git
git push --force --set-upstream origin main
```

После force-push:
- [ ] VPS: `cd /opt/caos && git fetch origin && git reset --hard origin/main` (pull после переписывания истории не сработает);
- [ ] Все остальные клоны пересоздать с нуля;
- [ ] Проверить, что GitHub Actions Secrets не зависят от удалённых файлов;
- [ ] Включить branch protection на `main`: require "CAOS CI", запретить прямые push (только PR).

## 3. Что уже сделано в этом репозитории

- Удалены из HEAD: `setup_stepik_env.sh`, `check_index.sh`, `deploy_frontend.sh`, `create_thinkred_chain.py`; локально удалены `setup_google_env.sh`, `test_llm.sh`.
- `.gitignore` переписан чистым UTF-8 (прежний файл был наполовину UTF-16 и не работал), добавлены `.env.*`, `.venv/`, `*.log`, `.coverage`.
- `deploy.yml`: секреты передаются через `env:` вместо интерполяции внутрь shell-скрипта; деплой запускается только после зелёного CI; убран `pytest -q || true`; добавлен health-check `curl /health`.
