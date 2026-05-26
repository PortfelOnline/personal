# 2026-05-26 — Прокси для Claude Code (Индия)

## Контекст

В Индии понадобился HTTPS-прокси для Claude Code (Anthropic API доступен,
но через прокси выходим с предсказуемым IP). Прокси:
`http://us401in200:***@185.232.171.138:9000`.

## Архитектура

**Единый источник истины — `~/.zshenv`** (а не `.zshrc`).
Причина: `.zshrc` грузится только в interactive zsh, а Claude Code запускает
внутренние Bash-команды как non-interactive zsh — там `.zshrc` не подхватился бы.
`.zshenv` грузится для **всех** zsh-сессий, включая non-interactive подоболочки.

**Дополнительный факт macOS:** Claude Code `Bash` tool использует `/bin/zsh`
(а не bash) — `echo $ZSH_VERSION` внутри инструмента даёт `5.9`. Значит
переменные из `.zshenv` доступны автоматически в каждом вызове.

## Файлы

### `~/.zshenv` (новый)

```sh
# Прокси для всех zsh-сессий, включая non-interactive (Claude Code Bash вызовы)
# localhost обходит прокси через no_proxy
export http_proxy='http://us401in200:***@185.232.171.138:9000'
export https_proxy='http://us401in200:***@185.232.171.138:9000'
export HTTP_PROXY="$http_proxy"
export HTTPS_PROXY="$https_proxy"
export no_proxy='localhost,127.0.0.1,::1'
export NO_PROXY="$no_proxy"
```

Зачем дублирование lower/UPPER — разные тулы читают разные.
`no_proxy=localhost` критично: иначе `cl-ds` (`ANTHROPIC_BASE_URL=http://127.0.0.1:8099`)
попытается пройти к ds-proxy ЧЕРЕЗ внешний прокси и сломается.

### `~/.zshrc` — только аварийный обход

```sh
# Использовать `claude-noproxy ...` чтобы запустить claude без прокси
claude-noproxy() {
  http_proxy="" https_proxy="" HTTP_PROXY="" HTTPS_PROXY="" \
    command claude "$@"
}
```

Без `unset/=""` — глобальные переменные из `.zshenv` всё равно унаследуются,
и обход не сработает. **Проверено: пустые proxy var возвращают реальный IP.**

`cl-pro`, `cl-ds` — остались **оригинальными alias**, ничего не переделывал.
Прокси к ним применяется автоматически через env из `.zshenv`.

## Грабли

1. **Сначала пытался обернуть `claude()` в `.zshrc`** — работало только для
   interactive shell. Внутри Claude Code `Bash` tool обёртка не применялась
   (хотя env-переменные были бы доступны через `.zshenv`).

2. **`claude-noproxy` без `unset/=""`** — НЕ отключает прокси, т.к. переменные
   глобальные. Нужно явно затирать.

3. **`no_proxy=localhost`** — без этого `cl-ds` через `127.0.0.1:8099` идёт
   в прокси и валится. Обязательно.

## Проверка

```sh
# С прокси (через .zshenv):
$ curl -s https://api.ipify.org
185.232.171.138

# Без прокси (через claude-noproxy):
$ claude-noproxy ...   # внутри — реальный IP 1.53.55.179
```

## Управление

- **Применить в открытых терминалах:** `source ~/.zshrc` (новые сессии — авто)
- **Сменить прокси:** правь только `~/.zshenv`, все обёртки используют env
- **Отключить:** закомментируй export-ы в `~/.zshenv`
- **Аварийный обход разово:** `claude-noproxy ...`

## Команды охвата

| Команда | Прокси? |
|---|---|
| `claude` | ✅ (через env из .zshenv) |
| `cl-pro` | ✅ |
| `cl-ds` | ✅ env + `no_proxy=localhost` обходит для самого ds-proxy |
| `claude-safe` | ✅ (вызывает `claude` внутри) |
| `claude-noproxy` | ❌ (намеренно — для отладки) |
| `curl`, `git`, `npm`, etc. в zsh | ✅ (зашит в env) |

## Связанное

- `~/.deepseek.env` + `cl-ds` → `ds-proxy.py` на `localhost:8099` (DeepSeek API)
- `~/claude-launcher.sh` (`cl`) — отдельный launcher, использует прокси через env
- Тема `cl-pro` уже фигурировала в коммитах `d3e47f6`, `94365a7`
