# 🧭 CAOS — Collective Activity Operating System

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**CAOS** — это цифровая платформа коллективного целеполагания. Она позволяет людям объединяться вокруг общих целей, а не вокруг формальных организационных структур.

> **Система, в которой первична цель, а люди временно присоединяются к её достижению.**

🔗 **Фронтенд:** [caos.thinkred.ru](https://caos.thinkred.ru) · **API:** [api-caos.thinkred.ru](https://api-caos.thinkred.ru) · **Проект:** [thinkred.ru](https://thinkred.ru)

---

## 📖 Что такое CAOS

Подробнее — в цикле статей на ThinkRed:
1. [Кризис самоорганизации XXI века](https://thinkred.ru/blog/crisis-of-self-organization.html)
2. [Цель как первичная единица](https://thinkred.ru/blog/goal-as-primary-unit.html)
3. [Диалектическое дерево целей](https://thinkred.ru/blog/dialectical-goal-tree.html)
4. [Программа РСДРП как граф целей](https://thinkred.ru/blog/rsdlp-as-goal-graph.html)
5. [Граф целей вместо структуры отделов](https://thinkred.ru/blog/goal-graph-instead-of-departments.html)
6. [Цифровой двойник и членство](https://thinkred.ru/blog/digital-twin-membership.html)
7. [Роль ИИ в целеполагании](https://thinkred.ru/blog/role-of-ai-in-collective-goal-setting.html)
8. [От кружка к 100 000 человек](https://thinkred.ru/blog/goal-graph-to-scale.html)

Коротко: CAOS заменяет иерархию людей графом целей. Вы не вступаете в организацию — вы присоединяетесь к достижению конкретной цели.

Внутреннее устройство домена описано в документации:
- [`docs/concept/ontology.md`](docs/concept/ontology.md) — онтология: Problem → Goal → Decision → Participation → Commitment → Activity → Result → Evidence → Verification
- [`docs/concept/invariants.md`](docs/concept/invariants.md) — инварианты-«конституция», исполняемые тестами
- [`docs/architecture/domain-model.md`](docs/architecture/domain-model.md) — целевая ER-модель и карта миграции
- [`docs/plan-caos-0.2.md`](docs/plan-caos-0.2.md) — план улучшений и его выполнение
- [`CHANGELOG.md`](CHANGELOG.md), [`CURRENT_STATE.md`](CURRENT_STATE.md) — история версий и текущее состояние

---

## 🚀 Быстрый старт

### Что нужно установить

1. **Docker Desktop** — скачать с [docker.com](https://www.docker.com/products/docker-desktop/)
2. **Git** — скачать с [git-scm.com](https://git-scm.com/)

### Запуск CAOS локально

```bash
# 1. Скачать код
git clone https://github.com/thethinkred-ai/caos-platform.git
cd caos-platform

# 2. Создать файл с настройками
cp .env.example .env

# 3. Запустить (Docker скачает всё сам)
docker compose up --build
```

Откройте:
- **Фронтенд:** http://localhost:5173
- **API:** http://localhost:8000/api/v1
- **Swagger-документация:** http://localhost:8000/docs — включается переменной `DEBUG=true` (в проде выключена; в `.env.example` она по умолчанию `false` — переверните для локальной работы)

> 🔧 Если что-то пошло не так — создайте [Issue](https://github.com/thethinkred-ai/caos-platform/issues/new).

### Локальная разработка без Docker (бэкенд)

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q                   # 102 теста
PYTHONPATH=. python -m uvicorn app.main:app --reload
```

Схема базы управляется Alembic: `PYTHONPATH=. python -m alembic upgrade head`.

---

## 🧩 Архитектура

```
caos-platform/
├── backend/                # FastAPI (Python 3.12)
│   ├── app/
│   │   ├── routers/        # API: auth, entities, goal_graph, goal_lifecycle,
│   │   │                   #   goal_participation, commitments, results,
│   │   │                   #   challenges, links, ai, search, ...
│   │   ├── models.py       # Модели SQLAlchemy (18+ таблиц)
│   │   ├── access.py       # Права доступа (что видно)
│   │   ├── permissions.py  # Матрица capabilities (что можно делать)
│   │   └── errors.py       # Доменные ошибки с кодами
│   ├── alembic/            # Миграции (0001–0007)
│   └── tests/              # 102 теста, включая инварианты INV-1..INV-11
├── frontend/               # React 19 + TypeScript + Vite
│   └── src/AppNew.tsx      # Приложение (монолит — реструктуризация в плане, Track F)
├── docs/                   # Онтология, инварианты, ER-модель, ADR, план
│   └── adr/                # Архитектурные решения
├── infrastructure/         # nginx-конфиги
└── docker-compose.yml
```

| Компонент | Технология |
|-----------|-----------|
| Бэкенд | Python + FastAPI + SQLAlchemy 2 |
| Фронтенд | React + TypeScript + Vite |
| База данных | PostgreSQL (прод, Alembic) / SQLite (тесты) |
| CI/CD | GitHub Actions: тесты → миграции → деплой на VPS |

### Ключевые механизмы домена

- **Граф целей**: типизированные рёбра `goal_relations` (concretizes / depends_on / supports / conflicts_with / contributes_to / blocks / supersedes) с защитой от циклов и анализом влияния `GET /goals/{id}/impact`.
- **Жизненный цикл цели**: `draft → proposed → accepted → active → achieved → verified → closed` — только серверными командами; цель с участниками принимается исключительно коллективным решением (`RECOGNITION_REQUIRED`).
- **Участие и обязательства**: контекстные роли (contributor / coordinator / expert / facilitator / observer) вместо членства в структурах; добровольные обязательства связывают задачи с целями.
- **Проверяемые результаты**: результат ≠ выполненная задача: `Result → Evidence → Verification`, причём автор результата не может верифицировать его сам.
- **Возражение как объект**: `Challenge` для целей, решений и результатов — с обязательным записанным ответом.
- **AI предлагает — люди решают**: каждый ответ AI сохраняется как предложение (модель, снимок входа, confidence) и влияет на домен только после человеческого ревью.
- **Контракт ошибок**: стабильные машиночитаемые коды (`INVALID_STATE_TRANSITION`, `SELF_VERIFICATION_FORBIDDEN`, …) поверх человекочитаемого `detail`.

---

## 🤝 Как помочь проекту

Мы ищем:
- **Python-разработчиков** — FastAPI, SQLAlchemy, Pydantic
- **React-разработчиков** — TypeScript, Vite
- **Проектировщиков** — онтология целей, процедуры целеполагания
- **Тестировщиков** — найти баги, предложить идеи
- **Авторов** — документация, статьи, переводы

### Пошаговая инструкция для первого Pull Request

1. Зарегистрируйтесь на **GitHub**
2. Зайдите на страницу проекта: https://github.com/thethinkred-ai/caos-platform
3. Нажмите **Fork** (кнопка справа вверху) — создаётся ваша копия
4. На своей копии нажмите **Code** → скопируйте ссылку
5. В терминале: `git clone <ваша-ссылка>`
6. Сделайте изменения, закоммитьте: `git add . && git commit -m "что сделали"`
7. Отправьте: `git push`
8. На GitHub нажмите **Contribute** → **Open Pull Request**
9. Опишите, что изменили, и нажмите **Create Pull Request**

Всё! Мы увидим и обсудим. CI проверит тесты и миграции автоматически.

---

## 📝 Контакты

- **Чат разработчиков:** [Telegram-группа](https://t.me/+5t6_LRJfbHswYjA6)
- **Основной канал:** [@thinkred_marx](https://t.me/thinkred_marx)
- **Создатель:** [thethinkred-ai](https://github.com/thethinkred-ai)

---

*MIT License — делайте с этим кодом что хотите, но указывайте оригинал.*
