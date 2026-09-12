# План улучшения CAOS 0.2 — на основе критики проекта

Основание: разбор «Критика проекта.txt» (16 шагов; фактические утверждения проверены по коду и подтверждены).
Главный вывод критики: сейчас CAOS — CRUD-система над **деревом** целей, а заявлен «граф целей» и координация вокруг целей. План перестраивает центр тяжести системы, не переписывая работающий прототип с нуля.

## Принципы плана

1. Порядок из самой критики: **онтология → инварианты → модель → авторизация → API → фронтенд → AI**. Фронтенд и AI — в конце, не в начале.
2. Эволюция, а не революция: каждая ступень = Alembic-миграция + тесты инвариантов + совместимость старого API.
3. Технический фундамент (Track 0) — предусловие: редизайн невозможно отлаживать на красных тестах и сломанном деплое.
4. Всё, что фиксируется в коде, сначала фиксируется в документах (Track B).

---

## Track 0 — Технический фундамент (предусловие)

- **0.1 Секреты**: ротация утёкших ключей (Stepik, Google, OpenRouter, FTP — вручную владельцем), удаление секретоносных скриптов, чистка git-истории (git filter-repo + force-push, после ротации), починка `.gitignore` (сейчас вторая половина — UTF-16 и не работает), убрать интерполяцию `${{ secrets.* }}` внутрь shell-скрипта в `deploy.yml`.
- **0.2 Баги авторизации**: `verify_password(None)` → 500 на OAuth-аккаунтах; вход по неподтверждённому email Google (takeover); OAuth-вход не создаёт `Session` → refresh всегда отклоняется; `verification_token` совмещает верификацию и сброс пароля, без TTL, открытым текстом; logout/смена пароля/удаление не отзывают сессии; user enumeration при регистрации; SMTP-ошибка после коммита → «вечный» неверифицированный аккаунт.
- **0.3 Тесты и деплой**: переписать тестовый набор (сейчас 100% красные: пароль против `min_length=12`, `/register` не возвращает токен, обязательна верификация email), убрать `pytest -q || true` из деплоя, деплой зависит от CI, ветка `main` + upstream + branch protection.
- **0.4 База**: Alembic вместо `create_all` и устаревших SQL-миграций; починить Postgres FTS (`search.py:46` — оператор `+` для конкатенации текста не существует в Postgres → `/search` даёт 500).
- **0.5 Гигиена фронтенда** (не зависит от модели): удалить мёртвый `App.tsx`, `request()` — обработка 204/401, зафиксировать версии зависимостей (уход от `"latest"`), `npm ci` + lockfile в Dockerfile, `tsc --noEmit` в build-скрипт, конфликт CSP vs Google Fonts (`nginx.conf` блокирует `@import` из `styles.css`).

Критерий M0: зелёный CI, деплой блокируется красными тестами, секреты ротированы.

---

## Track A — Быстрые исправления «10 дефектов» (без смены модели)

- **A1. Назначение задачи**: назначаемый обязан быть участником проекта (`entities.py:325-328` сейчас проверяет только существование пользователя).
- **A2. Право голоса**: голосовать могут только участники контекста цели (владелец цели, участники связанных проектов); решение без цели — только автор (`entities.py:349-364` сейчас пускает любого залогиненного).
- **A3. Честный `decision_method`**: default `"majority"` вместо `"consensus"` при подсчёте «простое большинство» (`models.py:108`, `entities.py:387-392`); whitelist методов; реализовать `majority` + `unanimity`; консенсус не заявлять, пока не реализована процедура.
- **A4. AI-контекст**: ретривал только из сущностей, доступных пользователю (переиспользовать `_user_goal_ids`/`_user_project_ids`); запрет чужих проблем/знаний в LLM-промпте (`ai.py:80-82, 105-106`).
- **A5. Публичный профиль**: отделить публичное представление пользователя (без `email`, без `stepik_id`) от собственного профиля (`schemas.py:18-25`).
- **A6. Секретность голосов**: наружу — агрегаты + собственный голос; `user_id` из `VoteOut` не отдавать до финализации решения.
- **A7. Доступ при создании связей**: `POST /goals` и `POST /projects` проверяют не только существование problem/goal, но и право доступа к ним (`entities.py:77-80, 166-167`).

Критерий: тест «красный → зелёный» на каждый дефект.

---

## Track B — Онтология 0.2 (бумага, до кода)

- **B1. `docs/concept/ontology.md`** — определения сущностей, по одной странице: Situation, Problem, Goal, GoalRelation, Participation, Commitment, Decision, Activity, Result, Evidence (+ Knowledge, Challenge, AIProposal).
- **B2. `docs/concept/invariants.md`** — 10 инвариантов Шага 16.24 критики как «конституция CAOS» + способ проверки каждого.
- **B3. `docs/architecture/domain-model.md`** — ER-модель 0.2 + карта «текущее → целевое» по каждой таблице models.py: оставить / переименовать / разделить / добавить / заморозить (Team).
- **B4. ADR**: `0002-goal-graph` (GoalRelation вместо parent_goal_id как фундамент), `0003-ai-boundary` (AI→Proposal→Human→Mutation), `0004-participation-vs-membership`.

Критерий: ревью владельцем; дальнейшие PR ссылаются на эти документы.

---

## Track C — Модель данных 0.2 (поэтапно, каждая ступень = миграция + тесты)

- **C1. Граф целей**: `GoalRelation(source_goal_id, target_goal_id, relation_type, rationale, author_id)`; типы: `concretizes, depends_on, supports, conflicts_with, contributes_to, blocks, supersedes`; `parent_goal_id` остаётся как сахар над `concretizes`; защита от запрещённых циклов; `GET /goals/{id}/relations` + анализ влияния («что остановится, если цель провалится»).
- **C2. Жизненный цикл цели**: GoalProposal; состояния `draft → proposed → under_review → accepted → active → achieved → verified → closed` (+ `rejected, suspended, abandoned, superseded`); переходы только серверными командами, произвольный PATCH статуса запрещён. Сегодня у цели нет жизненного цикла вообще — нет ни одного эндпоинта смены статуса.
- **C3. Участие**: `GoalParticipation(user, goal, role, status, visibility, joined_at, left_at)`; роли контекстные (contributor, coordinator, expert, facilitator, observer); `ProjectMember`/`TeamMember` уходят в тень, Team замораживаем (не развиваем, не удаляем).
- **C4. Обязательства**: `Commitment(user, goal, description, expected_result, success_criteria, deadline, source ∈ {self, decision, delegation}, status)`; Task привязывается через Commitment → «бесхозных» задач не остаётся (инвариант).
- **C5. Результаты и доказательства**: `Result(goal, activity, description, expected_state, actual_state, status, reported_by)` + `Evidence(result, type, content, source)`; `reported ≠ verified`; верификатор ≠ исполнитель; baseline/target/actual у критериев цели.
- **C6. Решение как процесс**: `ProposalVersion`; типы событий `argument, objection, question, alternative, revision`; `Challenge` для Goal/Decision/Result (claim, argument, evidence, alternative); честные методы (`majority, unanimity, consent, delegated`); срок действия решения (`valid_until, review_at`).
- **C7. Связности**: `ProjectGoal` (M2M проект↔цель вместо одиночного `Project.goal_id`); `KnowledgeRelation` (знание ↔ problem/goal/decision/result).

---

## Track D — Авторизация и приватность

- **D1. Объектные права**: `Can(user, action, object, context)` вместо шести копий owner/membership-проверок; матрица `view / join / propose / edit / challenge / close` для Goal; edit формулировки ≠ edit критерия успеха.
- **D2. Identity/Profile**: разделение `UserIdentity` (email, пароли) и `UserProfile` (display_name, bio); email не покидает личные эндпоинты; экспорт данных пользователем; при удалении аккаунта — анонимизация с сохранением вклада в историю («Удалённый участник»).
- **D3. Классы данных**: PUBLIC / INTERNAL / PERSONAL / SENSITIVE / RESTRICTED; privacy-фильтрация между доменом и API-представлением (сейчас «SQLAlchemy → Pydantic → JSON» без слоёв).
- **D4. Аудит**: append-only; история объекта (по `entity_id`), а не только действия текущего пользователя.

---

## Track E — API команд и инварианты в CI

- **E1. Действия вместо голого CRUD**: `POST /goals/{id}/propose | challenge | accept | activate | join | commit | report-result | verify | close`; `POST /decisions/{id}/open | vote | finalize | appeal`; произвольные PUT-статусы уходят.
- **E2. Тесты инвариантов в CI**: `activity_requires_goal`, `ai_cannot_mutate_domain`, `no_verified_result_without_evidence`, `no_orphan_tasks`, допустимые переходы state machine, граф без запрещённых циклов, делегирование с истечением срока.

---

## Track F — Фронтенд Goal-centric (только после C1–C5)

- Страница цели как «мини-организация»: Обзор / Граф / Деятельность / Участники / Решения / Результаты / История.
- «Моя деятельность» (мои обязательства, блокировки, ожидаемые решения) вместо «Мои проекты».
- Explain-this: двунаправленная трассировка Problem → Goal → Decision → Commitment → Task → Result.
- Вход через один вопрос («Что вы хотите изменить?») с progressive disclosure; создание цели доступно наравне с созданием проблемы (сейчас вход только через проблему, `AppNew.tsx:486`).
- Попутно — реструктуризация: разбивка `AppNew.tsx` на компоненты/секции, api-слой, роутер.

---

## Track G — AI-слой (после D)

- **G1. AIProposal вместо AISuggestion**: model/version, input_snapshot, proposed_change, rationale, confidence, status, reviewed_by; единственный путь изменения домена: AI → Proposal → Human review → Mutation.
- **G2. AI Context Firewall**: минимальный контекст по классам данных; permission-scoped retrieval; никаких email/bio/OAuth-данных в промптах.
- **G3. Режимы**: analyst / critic / researcher / planner / auditor; реальный retrieval на поиске по БД вместо «первых 5 записей».
- **G4. Память AI**: сохранение prompt/model/output/оценки предложений; метрики принятых/отклонённых.

---

## Track H — Governance и Safety (дальняя перспектива, по мере роста сообщества)

- Делегирование полномочий с scope и сроком; принцип двух ключей для критических операций.
- Safety-скрининг предложений (GREEN/YELLOW/RED) до признания цели + независимая апелляция.
- Аварийные режимы с автоматическим истечением полномочий; разделение Security Admin / Auditor.

---

## Что НЕ делать (запреты из критики)

- Микросервисы, Neo4j, Kafka — преждевременно; модульный монолит + PostgreSQL (recursive CTE хватает).
- Redux / тяжёлый state-management на текущем размере фронтенда.
- Новый красивый фронтенд поверх старой модели.
- Физический DELETE ключевых сущностей — только смены состояний (archive / supersede / withdraw).
- «Диалектические» имена в API/таблицах — только инженерные названия.
- Единый глобальный числовой приоритет целей; любые рейтинги/KPI людей.

## Что остаётся как есть (критика подтвердила)

FastAPI + PostgreSQL + React/TS; разделение Problem/Goal/Decision/Project/Task; `DecisionEvent` (основа для процесса решений); аудит-трейл (основа для истории объекта); компетенции (связать с целями в C3–C4); OAuth; уведомления; Docker-разделение backend/frontend.

---

## Порядок исполнения и вехи

| # | Этап | Треки | Веха |
|---|------|-------|------|
| 1 | Честный фундамент | 0 → A | **M1**: CI зелёный, дефекты закрыты, деплой безопасен |
| 2 | Онтология зафиксирована | B | **M2**: доки ревью приняты (можно параллельно с 0/A) |
| 3 | Граф и жизненный цикл целей | C1, C2, E1 | **M3**: цель — объект с процедурой, граф настоящий |
| 4 | Участие и обязательства | C3, C4, D1 | **M4**: человек участвует в цели, задачи не бесхозные |
| 5 | Проверяемые результаты | C5, C6, E2 | **M5**: результат ≠ задача, решение — процесс |
| 6 | Фронтенд вокруг цели | F | **M6**: Goal Explorer, «Моя деятельность» |
| 7 | AI-советник | G | **M7**: AI предлагает, человек решает |
| 8 | Governance/Safety | H | по мере роста сообщества |

После каждой ступени: коммит, зелёный CI, деплой.
