# Диагностика: kadastrmap.info лагает после миграции на сервер n

**Дата:** 2026-04-30  
**Серверы:** n (167.86.116.15, Contabo) + proxy (194.55.239.189, LandVPS)

---

## Архитектура

```
Интернет → LandVPS proxy (194.55.239.189:443)
          → SSH-туннели (8083/8084 → n:8082)
          → Docker «kad» (контейнер на n)
          → PHP 7.4 + MySQL + Manticore + Redis
```

**Proxy (LandVPS):**
- nginx reverse proxy с SSL termination
- Два SSH-туннеля для failover (основной + backup)
- upstream `kad_backend` → `127.0.0.1:8083` (failover: 8084)
- Load: 0.00 — простой

**Backend n (Contabo vmi992973):**
- Hostname: vmi992973.contaboserver.net
- Uptime: 109 дней
- Load average: **~9.5** из ~16 vCPU
- RAM: 15GiB, 7.1GiB used
- Swap: 4GiB, **2.5GiB used** — подкачка активна
- Диск: 391GB, 65% used

---

## Причины лагов

### 1. Высокая нагрузка CPU (load ~9.5)

**Главные потребители:**

| Процесс | CPU | RAM | Заметки |
|---------|-----|-----|---------|
| mysqld (внутри kad) | 9.6% | 21.9% (3.6GB) | buffer_pool=3.2GB |
| dockerd | 10% | 1% | Аномально высокий CPU |
| searchd (Manticore) | 2.1% | 12.8% (2GB) | Поисковый движок |
| php-fpm workers | 3-5% | 0.4% | Пару активных воркеров |
| docker-compose (×7) | ~3% | — | Каждый в фоне |

**Вывод:** MySQL + Docker демон пожирают CPU. Load ~9.5 означает очередь на CPU.

### 2. Давление памяти (swap 2.5GB из 4GB)

- swap активен — значит хотя бы временно RAM не хватало
- InnoDB buffer pool = 3.2GB
- Manticore = 2GB
- Redis (kad) = 720MB
- Docker overlay/volumes

### 3. MySQL без slow_query_log

- Slow log выключен
- long_query_time = 10s (должен быть 2-3s)
- Максимум подключений: 67 (лимит 150)
- **206 slow queries** зафиксировано — диагностировать невозможно

### 4. PHP-FPM: PHP 7.4 (устарел)

- PHP 7.4.33 (EOL: Nov 2022)
- Минимальное количество pm workers
- В контейнере всего 2 php-fpm workers активно

### 5. SSH-туннель как единая точка отказа

- Весь трафик проходит через SSH-туннели (LandVPS → Contabo)
- При перегрузке бэкенда туннель тупит, proxy отдаёт timeout
- HetrixTools закономерно видит timeout (10s) из разных регионов

### 6. Docker демон ест 10% CPU

- dockerd постоянно жрёт 10% CPU — аномалия
- Возможно, из-за множества docker-compose процессов (8 штук)
- overlay2, volumes, network bridge создают нагрузку

---

## Расход токенов AI

### n8n — 43 воркфлоу, 25 активных

**Активные AI-воркфлоу (потенциально жрут токены):**

| Воркфлоу | Ноды | AI нод | Тип |
|----------|------|--------|-----|
| Sites Admin - Website Crawler | 40 | 4 | Скрапинг + AI |
| GMA Chat | 11 | 3 | Чат с AI |
| AI Consultant - DataTables v1 | 8 | 2 | AI-консультант |
| AI Consultant - Brain Skill | 8 | 4 | Brain Skill |
| AI Consultant - Universal v1 | 14 | 5 | Универсальный |
| Brain Skill RAG (×4) | 6-8 | 2-3 | RAG |
| Mobile4U Content (×2) | 15-18 | 2-3 | Генерация контента |
| SEO Content | 25 | 3 | SEO Perplexity |
| Get My Agent — Chat | 8 | 2 | Чат |

**Всего: ~18 воркфлоу с AI, активны ~12+**

**API-ключи:**
- `OPENAI_API_KEY` в n8n

### deepseek-agent
- Использует DeepSeek API (`DEEPSEEK_API_KEY`)
- Работает как AI-агент с доступом к docker.sock

### aiwaiter
- Собственный AI-сервис (порт 4100)
- PostgreSQL бэкенд

---

## Вывод

**Сайт лагает из-за перегрузки CPU на сервере n.** MySQL — главный потребитель. SSH-туннели добавляют latency. AI-воркфлоу n8n создают дополнительную нагрузку на API и процессор.

### Что делать (рекомендации)

1. **Включить slow_query_log** в MySQL (long_query_time=3s)
2. **Оптимизировать MySQL** — проверить индексы, таблицы
3. **Почистить неиспользуемые docker-compose** — много летающих EFK-стеков
4. **Проверить dockerd** — 10% CPU аномалия
5. **Обновить PHP 7.4 → 8.x** — устарел, не получает патчей
6. **Для токенов AI** — проверить частоту выполнения n8n воркфлоу (возможно, какие-то работают по расписанию)
