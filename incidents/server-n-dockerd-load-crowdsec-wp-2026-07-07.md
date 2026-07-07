# High Load — dockerd spin на удалённых логах + защита WP в CrowdSec (2026-07-07)

**Сервер**: n (167.86.116.15, Contabo, 6 CPU / 16 ГБ)
**Триггер**: Zabbix «Load average is too high» — load ~9–10 при 6 CPU, с ~16:43 (Zabbix) / ~21:43 ICT.
**Влияние на сайт**: НЕТ. 100zem.ru и kadastrmap.info всё время отвечали штатно (0.2–0.9 с, HTTP 200/301). Load был чисто фоновым.

---

## Часть 1 — Load на сервере

### Root Cause
`dockerd` крутил **~200–212% CPU** (2 ядра), iowait=0, высокий sy.
- `strace -f -e trace=pread64` → ~3000 pread64 за 2 с по двум fd (149, 34).
- `ls -l /proc/<dockerd>/fd/149,34` → оба указывают на `*-json.log (deleted)` контейнеров `a8373fe8`, `7bc0a607`, которых **уже нет** (`docker ps -a` их не знает).
- Вывод: после `docker rm`/recreate/ротации лога горутина лог-коллектора dockerd не завершилась и застряла, вычитывая мёртвый (deleted) inode в бесконечном цикле (futex 59% + pread шторм). Docker 29.6.0, json-file driver.
- `lsof -U | grep docker.sock` — внешнего API-шторма нет (только dockerd+systemd держат sock; Zabbix docker-плагин не настроен). Т.е. патология внутренняя.

Побочно: паразитный busy-loop `bash -c until …; false; do :; done` от старого запуска `/root/grid-mainnet` (aitrading) — крутил `do :; done` без sleep ~1.5 дня, ~10% CPU впустую.

### Resolution
1. `kill <busy-loop-pid>` — убрал паразитный bash (−10% CPU).
2. `systemctl restart docker` — `live-restore=true` (в daemon.json) → **все 21 контейнер пережили рестарт, сайт не падал**, прервалось лишь управление Docker на ~2–5 с.

### Results
- dockerd: **212% → 3.9%** CPU, мёртвые fd 2 → 0.
- Load пошёл вниз (10 → ~7 → норма для этого сервера).
- Все контейнеры healthy.

### Диагностические заметки
- `top -bn2 -d 2` (второй проход = реальная дельта). `top -bn1` / `ps pcpu` дают среднее за жизнь процесса — врут (показывали dockerd 229% как «накопительное»).
- `docker stats --no-stream` — мгновенный CPU по контейнерам (был умеренный → значит жрёт сам демон).
- ❌ НЕ делать `grep -l "socket:\[ino\]" /proc/*/fd/*` — вешается на ~1400 процессах и сам грузит сервер.
- Отличие от инцидента 2026-06-22 (dockerd SIGSEGV + systemd-дедлок): там был краш демона; тут — плановый рестарт здорового демона, прошёл чисто.

### Prevention
- При «dockerd жрёт ядра без явной причины» — сразу проверять `ls -l /proc/<dockerd>/fd | grep 'json.log (deleted)'`.
- Лечение — `systemctl restart docker` (безопасно при `live-restore: true`).

---

## Часть 2 — CrowdSec: закрыта дыра брутфорса WordPress

### Проблема
В логах `wp-shared-nginx` — брутфорс `POST /wp-login.php` (напр. 152.228.213.32 на shared-brains.ru, короткий всплеск ~14:43 UTC). CrowdSec его **не банил и даже не алертил**.

Причина:
- CrowdSec **читает** лог wp-shared-nginx (docker-acquisition, `/etc/crowdsec/acquis.d/wp-shared.yaml`, type: nginx; метрики — 67.7k строк распарсено). Источник ОК.
- Но не было сценария на брутфорс логина: collection `crowdsecurity/wordpress` не установлена.
- Установленные `http-generic-bf` и `http-wordpress-scan` триггерятся на **4xx**. А WordPress на неверный логин отдаёт **HTTP 200** (перерисовывает форму) → серия попыток невидима.

### Fix
```bash
cscli collections install crowdsecurity/wordpress   # http-bf-wordpress_bf, http-wordpress_user-enum, http-wordpress_wpconfig
systemctl reload crowdsec
```

### Verification
Прогон 25 тестовых `POST /wp-login.php` от одного IP через движок (`cscli explain --file … --type nginx`):
- парсер `crowdsecurity/nginx-logs` → 🟢 success
- сценарий `crowdsecurity/http-bf-wordpress_bf` → 🟢 подхватывает каждое событие (наливает в leaky-bucket) → бан при серии.

Раньше эти запросы не матчились ни одним сценарием — дыра была полностью открыта.

**Статус**: ✅ обе задачи закрыты. CrowdSec active, bouncer'ы (firewall + nl-proxy) живы.
