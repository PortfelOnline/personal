# proxy4: три SSH-туннеля не пережили ребут сервера (2026-08-28)

## Summary
✅ Инцидент решён. Ребут `proxy4` 27.08.2026 в 11:23 MSK оставил **4 SSH-туннеля** (systemd
`Restart=always`) в состоянии `disabled` — они не поднялись после старта сервера. Один
(`lapi-tunnel`) уже был найден и починен 27.08 отдельно. При работе над жалобой «киоск aiwaiter
выглядит офлайн» 28.08 нашлись ещё три: `aiwaiter-tunnel`, `gma-tunnel`, `gma-tunnel2`,
`gma-app-tunnel`.

## Timeline
- **27.08 11:23 MSK** — плановый/непреднамеренный ребут `proxy4` (uptime сброшен).
- **27.08, ~08:01 UTC** — последний успешный heartbeat планшета aiwaiter (до этого туннель ещё
  работал; упал в районе ребута).
- **27.08** (отдельная сессия) — найден и починен `lapi-tunnel-watchdog` disabled-инцидент
  (`incident_proxy4_lapi_tunnel_disabled_outage_2026_08_27` в автопамяти).
- **28.08 ~13:00 ICT** — юзер заметил, что киоск aiwaiter в `/admin` показывает «офлайн», хотя
  на экране планшета нормально отображается меню.
- **28.08** — расследование показало: `aiwaiter-tunnel.service` (proxy4:8100→n:4100) был
  `disabled`+`inactive` с момента ребута — 22 часа простоя heartbeat/diag-poll для планшета.
  Экран не менялся, т.к. меню было закешировано локально — отсюда ложное «всё же работает».
- При системной проверке всех `*tunnel*` юнитов на proxy4 обнаружены ещё три в том же
  состоянии: `gma-tunnel.service` (8090→n:8089), `gma-tunnel2.service` (8091→n:8089),
  `gma-app-tunnel.service` (8094→n:443). Проверка `app.get-my-agent.com/widget/loader.js`
  подтвердила: живые 502 пользователям с 100zem.ru прямо в моменте.

## Root cause
`systemd Restart=always` защищает от падения процесса, но **не гарантирует автозапуск после
ребута хоста**, если юнит не `enabled` (не залинкован в `multi-user.target.wants`). Неизвестно,
когда именно эти 4 юнита стали disabled — либо ручное `systemctl disable` в прошлом (забытое
после какой-то диагностики), либо они изначально создавались без `enable`. Ребут просто проявил
уже существующую проблему конфигурации сразу для всех четырёх разом.

## Fix
- `systemctl enable --now` для всех четырёх: `aiwaiter-tunnel`, `gma-tunnel`, `gma-tunnel2`,
  `gma-app-tunnel` (плюс ранее — `lapi-tunnel`).
- Для каждого добавлен персональный **health-check watchdog** (timer раз в минуту + скрипт),
  по образцу уже существующих `kad-tunnel-watchdog`/`lapi-tunnel-watchdog`: curl на локальный
  порт туннеля, после 3 неудач подряд — `systemctl restart`. Это ловит не только падение
  процесса (что уже покрыто `Restart=always`), но и «залипший, но живой» ssh (процесс есть,
  форвардинг не отвечает) — паттерн из более раннего инцидента с 8 kad-туннелями.
  - `/usr/local/bin/aiwaiter-tunnel-watchdog.sh` + `aiwaiter-tunnel-watchdog.{service,timer}`
  - `/usr/local/bin/gma-tunnel-watchdog.sh` (проверяет все 3 gma-порта) +
    `gma-tunnel-watchdog.{service,timer}`

## Verification
- `docker logs aiwaiter | grep kiosk/heartbeat` — heartbeat снова идёт раз в минуту, `201`.
- `curl https://app.get-my-agent.com/widget/loader.js` → `200` (было `502`).
- `systemctl is-enabled` на всех 5 туннелей proxy4 → `enabled`; таймеры watchdog видны в
  `systemctl list-timers`.

## Lessons / future protection
- 🚨 **Проверять `systemctl is-enabled`, а не только `is-active`**, для любого SSH-туннеля на
  proxy4/proxy2/proxy3 после каждого ребута хоста — `Restart=always` создаёт ложное чувство
  надёжности, но не покрывает «не стартовал вообще».
- Стоит завести на proxy4 разовый общий чек-скрипт: `systemctl list-unit-files '*.service' |
  grep tunnel`, сверять enabled/active для ВСЕХ туннелей сразу — этот способ и нашёл gma-* здесь
  за один проход, вместо поочерёдных инцидентов по одному сервису.
- Если после ребута proxy4 что-то в проде «внезапно молчит», первым делом сравнивать: время
  последнего успешного запроса в логах бэкенда vs время ребута `uptime`/`last reboot -F` на
  proxy4/proxy2/proxy3, а не искать баг в коде приложения.

Связано: `incident_proxy4_lapi_tunnel_disabled_outage_2026_08_27`,
`incident_aiwaiter_proxy4_tunnel_disabled_offline_2026_08_28` (автопамять Claude).
