# 🧭 CAOS — Collective Activity Operating System

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**CAOS** — это цифровая платформа коллективного целеполагания. Она позволяет людям объединяться вокруг общих целей, а не вокруг формальных организационных структур.

> **Система, в которой первична цель, а люди временно присоединяются к её достижению.**

🔗 **Фронтенд:** [caos.thinkred.ru](https://caos.thinkred.ru) · **API:** [api-caos.thinkred.ru](https://api-caos.thinkred.ru/docs) · **Проект:** [thinkred.ru](https://thinkred.ru)

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
- **API:** http://localhost:8000
- **Swagger-документация:** http://localhost:8000/docs

> 🔧 Если что-то пошло не так — создайте [Issue](https://github.com/thethinkred-ai/caos-platform/issues/new).

---

## 🧩 Архитектура

```
caos-platform/
├── backend/           # FastAPI (Python)
│   ├── app/           # Код приложения
│   │   ├── routers/   # API endpoints
│   │   ├── models.py  # Модели базы данных
│   │   └── main.py    # Точка входа
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/          # React + TypeScript + Vite
│   ├── src/
│   │   ├── App.tsx    # Главный компонент
│   │   └── main.tsx   # Точка входа
│   └── package.json
└── docker-compose.yml
```

| Компонент | Технология |
|-----------|-----------|
| Бэкенд | Python + FastAPI |
| Фронтенд | React + TypeScript + Vite |
| База данных | PostgreSQL (прод) / SQLite (тесты) |
| Кеш | Redis |

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

Всё! Мы увидим и обсудим.

---

## 📝 Контакты

- **Чат разработчиков:** [Telegram-группа](https://t.me/+5t6_LRJfbHswYjA6)
- **Основной канал:** [@thinkred_marx](https://t.me/thinkred_marx)
- **Создатель:** [thethinkred-ai](https://github.com/thethinkred-ai)

---

*MIT License — делайте с этим кодом что хотите, но указывайте оригинал.*
