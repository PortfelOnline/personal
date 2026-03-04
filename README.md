# Strategy Dashboard

Монорепо с двумя приложениями:

| Приложение | Порт | Назначение |
|------------|------|-----------|
| **strategy-dashboard** | 3000 | AI-дашборд: генерация контента, контент-календарь, боты |
| **bot-dashboard** | 4000 | Мини-дашборд управления ботами (standalone, без авторизации) |

---

## bot-dashboard — быстрый старт

> Нужен только **Node.js 18+**. Не нужны npm/pnpm/Python/конфиг.

```bash
git clone https://github.com/PortfelOnline/strategy-dashboard
cd strategy-dashboard/bot-dashboard
./start.sh
# → http://localhost:4000
```

`BOT_DIR` определяется автоматически — сначала ищется `~/yandex_bot`, потом соседние папки.

**Если yandex_bot лежит в нестандартном месте** — создать `.env` рядом со `start.sh`:
```
BOT_DIR=/другой/путь/к/yandex_bot
PORT=4000
```

### Вкладки

| Вкладка | Что делает |
|---------|-----------|
| **Боты** | Запуск/остановка/логи, warmup_days, последний запуск, кол-во запросов |
| **Прокси** | Добавить/заменить/удалить proxies.txt, статус бана (капча) |
| **Google Docs** | Ссылки на документы с поисковыми запросами, по сайтам |
| **Автопилот** | Оркестратор: авто-запуск, warmup→target, задержка перезапуска, суточное окно |

### Автопилот

1. Открыть вкладку **Автопилот**
2. Добавить боты: Bot ID + сайт
3. Настроить параметры (всё уже по умолчанию разумное):
   - Макс. одновременно: **3**
   - Задержка перезапуска: **30 мин**
   - Суточное окно: **8:00–22:00**
4. Включить тумблер → **Сохранить конфиг**

Режим определяется автоматически: `warmup_days < 14` → `warmup`, иначе `target`.
Тик каждые 30 секунд. Конфиг перечитывается на каждом тике.

### Файлы yandex_bot (что читает/пишет дашборд)

```
~/yandex_bot/
├── proxies.txt                         ← список прокси
├── outputs/
│   ├── proxy_cache.json                ← кэш проверенных прокси (TTL 1ч)
│   ├── proxy_blacklist.json            ← забаненные прокси (после капчи)
│   ├── orchestrator.json               ← конфиг автопилота
│   ├── google_docs.json                ← URL Google-документов
│   └── bot_states/
│       └── bot_N_state.json            ← состояние каждого бота
└── logs/
    └── bot_N.log                       ← логи каждого бота
```

### Пересборка (для разработчика)

```bash
cd bot-dashboard
pnpm install
pnpm dev          # dev-режим с hot reload
bash build.sh     # пересобрать release/ (коммитить после изменений)
```

---

## strategy-dashboard — основной дашборд

### Требования

- Node.js 18+
- pnpm
- MySQL 8+

### Установка

```bash
# 1. Зависимости
pnpm install

# 2. Конфиг
cp .env.example .env   # или создать .env вручную (см. ниже)

# 3. MySQL — создать БД и применить миграции
mysql -u root -e "CREATE DATABASE IF NOT EXISTS strategy_dashboard;"
pnpm db:push

# 4. Запуск
pnpm dev   # → http://localhost:3000
```

### .env (минимум для локального запуска)

```env
PORT=3000
NODE_ENV=development

JWT_SECRET=any-random-string-here

DATABASE_URL=mysql://root@localhost:3306/strategy_dashboard

# Путь к папке yandex_bot
BOT_DIR=/Users/yourname/yandex_bot

# AI (необязательно для локального dev)
BUILT_IN_FORGE_API_URL=
BUILT_IN_FORGE_API_KEY=

# OAuth — не нужен локально, используй /api/dev/login
VITE_APP_ID=dev-local
OWNER_OPEN_ID=dev-user-local
```

### Вход в dev-режиме

Открыть: `http://localhost:3000/api/dev/login` — создаёт сессию без OAuth.

### Страницы

| URL | Страница |
|-----|---------|
| `/` | Главная (навигация) |
| `/generate` | Генератор контента (AI) |
| `/library` | Библиотека контента |
| `/calendar` | Контент-календарь |
| `/accounts` | Meta-аккаунты (Facebook/Instagram) |
| `/bots` | Управление ботами (встроено в основной дашборд) |

### Команды

```bash
pnpm dev          # dev-сервер (порт 3000)
pnpm check        # TypeScript проверка
pnpm build        # production-сборка
pnpm test         # тесты (Vitest)
pnpm db:push      # применить миграции БД
pnpm format       # Prettier
```

### Стек

- **Frontend**: React 19, Vite, Tailwind v4, shadcn/ui, tRPC, TanStack Query
- **Backend**: Express, tRPC v11, Drizzle ORM, MySQL2, jose (JWT)
- **Боты**: Python 3 + Selenium + Firefox (yandex_bot — отдельный репо)

---

## Структура репо

```
strategy-dashboard/
├── bot-dashboard/          ← standalone мини-дашборд для ботов
│   ├── release/            ← pre-built (Node.js only, без npm)
│   │   ├── server.cjs      ← весь сервер в одном файле
│   │   └── public/         ← собранный фронт
│   ├── server/             ← исходники сервера
│   ├── src/                ← исходники фронта (React)
│   ├── start.sh            ← запуск (node release/server.cjs)
│   └── build.sh            ← пересборка release/
├── client/                 ← фронт основного дашборда
├── server/                 ← бэкенд основного дашборда
│   ├── bots.ts             ← управление процессами ботов
│   ├── orchestrator.ts     ← планировщик ботов
│   └── routers/bots.ts     ← tRPC роутер для ботов
├── shared/                 ← общие типы
├── drizzle/                ← схема и миграции БД
└── .env                    ← конфиг (не в git)
```

---

## Связанные репозитории

- **yandex_bot** — `github.com/PortfelOnline/yandex_bot`
  Python-бот: Selenium + Firefox, антидетект, прокси-ротация, прогрев профиля
