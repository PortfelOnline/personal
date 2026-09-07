# Kwork Email Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Получать официальные email-уведомления Биржи Kwork, отбирать релевантные проекты и присылать в Telegram ссылку с черновиком отклика, никогда не обращаясь к Kwork программно.

**Architecture:** Одноразовый Python-процесс, вызываемый cron, читает новые письма выделенного IMAP-ящика и ведёт курсор и статусы в SQLite. Он разбирает уведомления, фильтрует проекты, при необходимости генерирует черновик через уже существующий OpenAI-совместимый мост и доставляет сообщение в Telegram; запись о доставке фиксируется только после успешного ответа Telegram.

**Tech Stack:** Python 3.11+, стандартные `email`/`imaplib`/`sqlite3`, PyYAML, requests, pytest, cron.

**Spec:** `docs/superpowers/specs/2026-09-02-kwork-monitor-design.md`

## Global Constraints

- Скрипт не делает HTTP-запросов к `kwork.ru`, не использует browser automation, cookie или скрапинг HTML Kwork.
- Единственный вход — официальные email-уведомления Kwork в выделенном ящике; фильтр проверяет разрешённого отправителя и тему до обработки тела письма.
- Отклик в Kwork никогда не отправляется автоматически: Telegram содержит только черновик и ссылку, финальное действие выполняет пользователь вручную.
- Секреты не попадают в Git: IMAP, Telegram и Code Assist берутся только из файла окружения с правами `0600`.
- Рабочая директория на сервере: `/root/kwork-monitor`; cron запускает процесс раз в час и не создаёт постоянный сервис.
- При недоступности Telegram курсор не продвигается и письмо будет повторено. Ошибка генерации не блокирует уведомление со ссылкой.
- `--dry-run` не пишет в SQLite и не отправляет Telegram; запрос генерации допускается только при явном `--with-generation`.

---

## File Structure

Все файлы ниже создаются в новом репозитории/директории `/root/kwork-monitor` при реализации.

| Path | Responsibility |
|---|---|
| `pyproject.toml` | Версия Python, runtime/test-зависимости и pytest configuration. |
| `config.example.yaml` | Несекретные настройки IMAP-папки, разрешённых отправителей/тем, ключевых слов и порогов. |
| `PROFILE.example.md` | Проверяемый стартовый бриф для генерации; рабочий `PROFILE.md` создаётся оператором и не попадает в Git. |
| `.gitignore` | Исключает `config.yaml`, `.env`, SQLite и логи. |
| `src/kwork_monitor/models.py` | Неизменяемые модели сообщения, настроек и результата доставки. |
| `src/kwork_monitor/config.py` | Загружает YAML и обязательные секреты окружения, валидирует конфигурацию. |
| `src/kwork_monitor/email_parser.py` | Преобразует raw RFC 822 email в проект либо контролируемую ошибку разбора. |
| `src/kwork_monitor/imap_source.py` | Читает новые UID из IMAP без изменения флагов сообщений. |
| `src/kwork_monitor/store.py` | SQLite-курсор, дедупликация, статусы и транзакции. |
| `src/kwork_monitor/relevance.py` | Детерминированный фильтр по ключевым словам и рубрикам. |
| `src/kwork_monitor/proposal.py` | Узкий клиент OpenAI-совместимого Code Assist моста. |
| `src/kwork_monitor/telegram.py` | Формирует ограниченное по размеру Telegram-сообщение и доставляет его через Bot API. |
| `src/kwork_monitor/runner.py` | Оркестрация одного тика, блокировка параллельных запусков, dry-run и коды выхода. |
| `src/kwork_monitor/cli.py` | Аргументы CLI и настройка логов. |
| `tests/fixtures/*.eml` | Санитизированные письма: валидное, нерелевантное и с изменённым шаблоном. |
| `tests/test_*.py` | Изолированные тесты компонент и один end-to-end тест с фейковыми портами. |
| `README.md` | Установка, ручная настройка Kwork-уведомлений, секреты, dry-run, cron и восстановление. |

## Task 1: Bootstrap, Models, and Safe Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `config.example.yaml`
- Create: `PROFILE.example.md`
- Create: `src/kwork_monitor/__init__.py`
- Create: `src/kwork_monitor/models.py`
- Create: `src/kwork_monitor/config.py`
- Create: `tests/conftest.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Settings`, `SecretSettings`, `ProjectEmail`, `DeliveryResult` from `models.py`.
- Produces: `load_settings(config_path: Path, environ: Mapping[str, str]) -> tuple[Settings, SecretSettings]`.
- Consumes later: every component receives the typed settings instead of reading files or environment itself.

- [ ] **Step 1: Write failing configuration tests**

```python
def valid_test_environ() -> dict[str, str]:
    keys = (
        "KWORK_IMAP_USERNAME", "KWORK_IMAP_" + "PASSWORD",
        "KWORK_TELEGRAM_BOT_TOKEN", "KWORK_TELEGRAM_CHAT_ID",
        "KWORK_CODEASSIST_BASE_URL",
    )
    values = ("monitor@example.test", "test-only", "token", "123", "http://127.0.0.1:8080/v1")
    return dict(zip(keys, values, strict=True))

def test_load_settings_reads_non_secret_yaml_and_secret_environment(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("imap:\n  host: imap.example.test\n  mailbox: INBOX\nfilters:\n  senders: [noreply@kwork.ru]\n  subject_patterns: ['Новый проект']\n  keywords: [python, бот]\n", encoding="utf-8")
    settings, secrets = load_settings(path, valid_test_environ())
    assert settings.imap.host == "imap.example.test"
    assert secrets.telegram_chat_id == "123"

def test_load_settings_rejects_missing_required_secret(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("imap: {host: imap.example.test, mailbox: INBOX}\nfilters: {senders: [noreply@kwork.ru], subject_patterns: [Новый], keywords: [python]}\n", encoding="utf-8")
    environ = valid_test_environ()
    environ.pop("KWORK_TELEGRAM_BOT_TOKEN")
    with pytest.raises(ConfigurationError, match="KWORK_TELEGRAM_BOT_TOKEN"):
        load_settings(path, environ)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_config.py -v`

Expected: FAIL because `kwork_monitor.config` does not exist.

- [ ] **Step 3: Add project metadata, models, and minimal configuration loader**

`pyproject.toml` must pin Python and dependencies as follows:

```toml
[project]
name = "kwork-monitor"
requires-python = ">=3.11"
dependencies = ["PyYAML>=6,<7", "requests>=2.32,<3"]

[project.optional-dependencies]
test = ["pytest>=8,<9", "requests-mock>=1.12,<2", "build>=1,<2"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

Define these minimum types and validate every field named in the example config:

```python
@dataclass(frozen=True)
class ProjectEmail:
    message_id: str
    uid: int
    subject: str
    project_url: str | None
    budget: str | None
    description: str | None

@dataclass(frozen=True)
class SecretSettings:
    imap_username: str
    imap_password: str
    telegram_bot_token: str
    telegram_chat_id: str
    codeassist_base_url: str
```

The loader must reject an absent YAML file, absent required environment variable, empty sender/subject/keyword list, and an `http://` or `https://` URL that does not end in `/v1`. Do not log secret values. `.gitignore` must exclude `.env`, `config.yaml`, `PROFILE.md`, `seen_orders.db`, `*.log`, and `kwork-monitor.lock`. `PROFILE.example.md` must contain only the verified skills from the specification (Python/PHP/Node.js, Telegram/WhatsApp bots, n8n automation, APIs, LLM integrations, parsing and VPS deployment) and instruct the model not to state a price, deadline, portfolio item, or experience claim not present in the profile or email.

- [ ] **Step 4: Run the focused tests**

Run: `python -m pytest tests/test_config.py -v`

Expected: PASS.

- [ ] **Step 5: Commit the bootstrap**

```bash
git add pyproject.toml .gitignore config.example.yaml src/kwork_monitor tests/test_config.py
git commit -m "feat: bootstrap Kwork email monitor configuration"
```

## Task 2: Parse a Kwork Notification Email Without Fetching Kwork

**Files:**
- Create: `src/kwork_monitor/email_parser.py`
- Create: `tests/fixtures/kwork_project_valid.eml`
- Create: `tests/fixtures/kwork_project_malformed.eml`
- Test: `tests/test_email_parser.py`

**Interfaces:**
- Consumes: raw RFC 822 `bytes` and IMAP UID from Task 3.
- Produces: `parse_project_email(raw: bytes, uid: int) -> ProjectEmail`.
- Produces: `EmailParseError(message_id: str | None, reason: str)` for a missing identity, subject, or project link.

- [ ] **Step 1: Write failing parser tests using sanitized fixtures**

```python
def test_parser_extracts_identity_link_budget_and_plain_text_description() -> None:
    project = parse_project_email(load_fixture("kwork_project_valid.eml"), uid=42)
    assert project.message_id == "<project-100@example.kwork.ru>"
    assert project.uid == 42
    assert project.project_url == "https://kwork.ru/projects/100"
    assert project.budget == "10 000 ₽"
    assert "Telegram-бот" in project.description

def test_parser_rejects_a_notification_without_project_link() -> None:
    with pytest.raises(EmailParseError, match="project URL"):
        parse_project_email(load_fixture("kwork_project_malformed.eml"), uid=43)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_email_parser.py -v`

Expected: FAIL because `parse_project_email` does not exist.

- [ ] **Step 3: Implement MIME-safe parsing and fixtures**

Use `email.policy.default` and `BytesParser`; prefer `text/plain`, otherwise convert `text/html` to whitespace-normalized text with `html.parser.HTMLParser`. Decode MIME headers with `email.header.decode_header`. Extract only HTTPS URLs whose hostname is exactly `kwork.ru`; do not follow a link. Budget extraction must preserve the matched text, and description must be capped at 6,000 characters before it reaches the generator.

```python
def parse_project_email(raw: bytes, uid: int) -> ProjectEmail:
    message = BytesParser(policy=policy.default).parsebytes(raw)
    message_id = message.get("Message-ID")
    subject = str(message.get("Subject", "")).strip()
    text = extract_body_text(message)
    url = extract_kwork_project_url(text)
    if not message_id or not subject or not url:
        raise EmailParseError(message_id, "missing Message-ID, subject, or project URL")
    return ProjectEmail(message_id=message_id, uid=uid, subject=subject,
                        project_url=url, budget=extract_budget(text),
                        description=truncate(text, 6000))
```

Fixtures must use only synthetic names, amounts and URLs. The first real notification is checked manually against the fixture before enabling cron; do not commit a real project email.

- [ ] **Step 4: Run parser tests**

Run: `python -m pytest tests/test_email_parser.py -v`

Expected: PASS.

- [ ] **Step 5: Commit parser work**

```bash
git add src/kwork_monitor/email_parser.py tests/test_email_parser.py tests/fixtures
git commit -m "feat: parse Kwork project notification emails"
```

## Task 3: IMAP Cursor and Durable Deduplication

**Files:**
- Create: `src/kwork_monitor/imap_source.py`
- Create: `src/kwork_monitor/store.py`
- Test: `tests/test_imap_source.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `Settings.imap`, `SecretSettings.imap_*`, and raw parser input from Task 2.
- Produces: `MailItem(uid: int, message_id: str | None, raw: bytes, from_address: str, subject: str)` and `ImapSource.fetch_after(uid: int) -> list[MailItem]`.
- Produces: `mail_key(message_id: str | None, uid: int) -> str`, returning the RFC `Message-ID` or the stable fallback `uid:<uid>`.
- Produces: `StateStore.get_cursor() -> int`, `StateStore.advance_cursor(uid: int) -> None`, `StateStore.is_recorded(key: str) -> bool`, and `StateStore.record(key: str, uid: int, status: str, error: str | None = None) -> None`.

- [ ] **Step 1: Write failing storage and IMAP tests**

```python
def test_store_keeps_cursor_and_deduplicates_message_id(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "seen_orders.db")
    assert store.get_cursor() == 0
    store.record("<a@test>", 7, "notified")
    store.advance_cursor(7)
    assert store.is_recorded("<a@test>") is True
    assert store.get_cursor() == 7

def test_source_returns_only_uids_after_cursor_and_never_marks_seen() -> None:
    client = FakeImapClient(messages={7: RAW_A, 8: RAW_B})
    source = ImapSource(client, allowed_senders={"noreply@kwork.ru"}, subject_patterns=("Новый проект",))
    assert [item.uid for item in source.fetch_after(7)] == [8]
    assert client.store_calls == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_store.py tests/test_imap_source.py -v`

Expected: FAIL because the state and IMAP modules do not exist.

- [ ] **Step 3: Implement SQLite schema and read-only IMAP adapter**

Create the following schema using parameterized SQL and WAL mode:

```sql
CREATE TABLE IF NOT EXISTS monitor_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS processed_messages (
    message_id TEXT PRIMARY KEY,
    uid INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('notified', 'ignored', 'parse_error')),
    error TEXT,
    created_at TEXT NOT NULL
);
```

`ImapSource` must use `UID SEARCH`, then `UID FETCH (RFC822.HEADER)` for each candidate, and fetch `RFC822` only after its normalized `From` and decoded `Subject` match `config.yaml`. Authenticate using `imaplib.IMAP4_SSL`, and never call `STORE`, `EXPUNGE`, `DELETE`, or set the `\\Seen` flag. The runner advances the cursor only after an item has been recorded as `notified`, `ignored`, or `parse_error`.

- [ ] **Step 4: Run storage and IMAP tests**

Run: `python -m pytest tests/test_store.py tests/test_imap_source.py -v`

Expected: PASS.

- [ ] **Step 5: Commit persistence and mail access**

```bash
git add src/kwork_monitor/imap_source.py src/kwork_monitor/store.py tests/test_imap_source.py tests/test_store.py
git commit -m "feat: add read-only IMAP cursor and monitor state"
```

## Task 4: Relevance, Draft Generation, and Telegram Delivery

**Files:**
- Create: `src/kwork_monitor/relevance.py`
- Create: `src/kwork_monitor/proposal.py`
- Create: `src/kwork_monitor/telegram.py`
- Test: `tests/test_relevance.py`
- Test: `tests/test_proposal.py`
- Test: `tests/test_telegram.py`

**Interfaces:**
- Consumes: `ProjectEmail`, profile text from `PROFILE.md`, configured keywords and Code Assist/Telegram secrets.
- Produces: `is_relevant(project: ProjectEmail, keywords: tuple[str, ...]) -> bool`.
- Produces: `ProposalClient.generate(project: ProjectEmail, profile: str) -> str` and raises `ProposalError` on unavailable/invalid responses.
- Produces: `TelegramNotifier.send(project: ProjectEmail, proposal: str | None, generation_error: str | None = None) -> DeliveryResult` and `TelegramNotifier.send_parse_error_alert(message_id: str | None, reason: str) -> DeliveryResult`.

- [ ] **Step 1: Write failing filtering, generation, and notification tests**

```python
def test_relevance_matches_case_insensitively_in_subject_or_description(project: ProjectEmail) -> None:
    assert is_relevant(project, ("ai-агент", "telegram-бот")) is True
    assert is_relevant(project, ("дизайн интерьера",)) is False

def test_generator_sends_profile_and_project_as_separate_messages(requests_mock, project: ProjectEmail) -> None:
    requests_mock.post("http://shim.test/v1/chat/completions", json={"choices": [{"message": {"content": "Готов подготовить бота."}}]})
    assert ProposalClient("http://shim.test/v1").generate(project, "Опыт: Python") == "Готов подготовить бота."

def test_telegram_message_includes_link_and_fallback_when_generation_failed(requests_mock, project: ProjectEmail) -> None:
    requests_mock.post("https://api.telegram.org/bottoken/sendMessage", json={"ok": True, "result": {"message_id": 77}})
    result = TelegramNotifier("token", "123").send(project, None, "timeout")
    assert result.message_id == 77
    assert "черновик не сгенерирован" in requests_mock.last_request.json()["text"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_relevance.py tests/test_proposal.py tests/test_telegram.py -v`

Expected: FAIL because the modules do not exist.

- [ ] **Step 3: Implement deterministic filter and bounded external clients**

Normalize text with `casefold()` and whitespace collapse; a project is relevant when any configured keyword occurs in `subject + description`. `ProposalClient` uses `POST {base_url}/chat/completions`, a 30-second timeout, and a system message which explicitly says: «Верни только короткий черновик отклика на русском; не утверждай факты, отсутствующие в проекте или профиле; если ТЗ неполное, задай один уточняющий вопрос». Do not include IMAP or Telegram secrets in prompts or logs.

`TelegramNotifier` uses `sendMessage` with `disable_web_page_preview=true`, HTML escaping, a 3,800-character message cap, and 15-second timeout. Message layout is exactly:

```text
<b>Новый проект Kwork</b>
<b>Тема:</b> {subject}
<b>Бюджет:</b> {budget or 'не указан'}
<a href="{project_url}">Открыть проект вручную</a>

<b>Черновик отклика</b>
{proposal or '⚠️ черновик не сгенерирован: {generation_error}'}
```

Return a `DeliveryResult` only when Telegram returns JSON `{"ok": true}`. Any HTTP error, malformed JSON, or `ok: false` raises `TelegramError`, so the runner will not record the message or advance its cursor.

- [ ] **Step 4: Run client tests**

Run: `python -m pytest tests/test_relevance.py tests/test_proposal.py tests/test_telegram.py -v`

Expected: PASS.

- [ ] **Step 5: Commit delivery pipeline components**

```bash
git add src/kwork_monitor/relevance.py src/kwork_monitor/proposal.py src/kwork_monitor/telegram.py tests/test_relevance.py tests/test_proposal.py tests/test_telegram.py
git commit -m "feat: filter projects and notify Telegram"
```

## Task 5: Tick Orchestration, Dry-run, and Failure Semantics

**Files:**
- Create: `src/kwork_monitor/runner.py`
- Create: `src/kwork_monitor/cli.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: all Task 1–4 interfaces through injected `mail_source`, `store`, `proposal_client`, and `notifier` protocols.
- Produces: `run_once(dependencies: Dependencies, *, dry_run: bool, with_generation: bool) -> RunSummary`.
- Produces: CLI commands `python -m kwork_monitor.cli --config /root/kwork-monitor/config.yaml [--dry-run] [--fixture path] [--with-generation]`.

- [ ] **Step 1: Write failing orchestration tests**

```python
def test_runner_records_and_advances_only_after_successful_telegram_delivery(deps: Dependencies) -> None:
    deps.notifier.send.return_value = DeliveryResult(message_id=9)
    summary = run_once(deps, dry_run=False, with_generation=True)
    assert summary.notified == 1
    assert deps.store.record.call_args.args[2] == "notified"
    assert deps.store.advance_cursor.call_args.args[0] == 101

def test_runner_does_not_advance_cursor_when_telegram_fails(deps: Dependencies) -> None:
    deps.notifier.send.side_effect = TelegramError("offline")
    summary = run_once(deps, dry_run=False, with_generation=True)
    assert summary.delivery_failures == 1
    deps.store.record.assert_not_called()
    deps.store.advance_cursor.assert_not_called()

def test_dry_run_neither_writes_state_nor_sends_telegram(deps: Dependencies) -> None:
    run_once(deps, dry_run=True, with_generation=False)
    deps.store.record.assert_not_called()
    deps.notifier.send.assert_not_called()
    deps.proposal_client.generate.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_runner.py -v`

Expected: FAIL because the runner is absent.

- [ ] **Step 3: Implement one-tick state machine and lock**

Use `fcntl.flock` on `/root/kwork-monitor/kwork-monitor.lock` with `LOCK_EX | LOCK_NB`; if another run owns it, log one line and return exit code `0`. Process items in ascending UID order. The exact branch semantics are:

```python
for item in source.fetch_after(store.get_cursor()):
    key = mail_key(item.message_id, item.uid)
    if store.is_recorded(key):
        store.advance_cursor(item.uid)
    elif parse_fails(item):
        notifier.send_parse_error_alert(item.message_id, reason)  # no record if alert fails
        store.record(key, item.uid, "parse_error", reason)
        store.advance_cursor(item.uid)
    elif not is_relevant(project, settings.filters.keywords):
        store.record(mail_key(project.message_id, item.uid), item.uid, "ignored")
        store.advance_cursor(item.uid)
    else:
        proposal = generate_or_none(project)
        notifier.send(project, proposal, generation_error)
        store.record(mail_key(project.message_id, item.uid), item.uid, "notified")
        store.advance_cursor(item.uid)
```

The dry-run branch logs the would-be action and executes neither `record`, `advance_cursor`, nor Telegram. It only calls Code Assist when both `--dry-run --with-generation` are present. IMAP authentication/configuration failures and unhandled exceptions return non-zero; a single delivery failure is logged and returns non-zero without hiding later failure diagnostics.

- [ ] **Step 4: Run orchestration tests and full suite**

Run: `python -m pytest -v`

Expected: PASS.

- [ ] **Step 5: Commit runnable monitor**

```bash
git add src/kwork_monitor/runner.py src/kwork_monitor/cli.py tests/test_runner.py
git commit -m "feat: run Kwork email monitoring tick"
```

## Task 6: Operational Documentation and Safe Server Installation

**Files:**
- Create: `README.md`
- Modify: `config.example.yaml`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: CLI in Task 5 and the user-provided Telegram/IMAP/Code Assist secrets.
- Produces: reproducible local test instructions and a manual cron installation procedure; it does not mutate production itself.

- [ ] **Step 1: Write failing CLI help and fixture dry-run tests**

```python
def test_cli_dry_run_with_fixture_succeeds_without_secrets(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "kwork_monitor.cli", "--dry-run", "--fixture", str(FIXTURE)],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0
    assert "would notify" in result.stdout
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`

Expected: FAIL because fixture-only dry-run still requires the production configuration.

- [ ] **Step 3: Document and implement the install-safe CLI path**

Allow `--fixture` only with `--dry-run`; it bypasses IMAP and reads a local `.eml`, but still applies parsing/filtering. `README.md` must include these exact manual preparation steps:

```bash
cd /root/kwork-monitor
python3.11 -m venv .venv
.venv/bin/pip install -e '.[test]'
install -m 600 /dev/null /root/kwork-monitor/.env
install -m 600 config.example.yaml /root/kwork-monitor/config.yaml
install -m 600 PROFILE.example.md /root/kwork-monitor/PROFILE.md
.venv/bin/python -m kwork_monitor.cli --dry-run --fixture tests/fixtures/kwork_project_valid.eml
```

It must also state: enable email notifications on the Kwork Биржа page manually, select relevant rubrics, use a dedicated mailbox/app password, set the `.env` variables, edit `PROFILE.md` to retain only accurate claims, check the first real notification by dry-run, and only then add this cron line:

```cron
17 * * * * cd /root/kwork-monitor && set -a && . ./.env && set +a && ./.venv/bin/python -m kwork_monitor.cli --config ./config.yaml >> ./kwork-monitor.log 2>&1
```

Document recovery: revoke and recreate a leaked app password or Telegram token, then replace only the server `.env`; do not put the replacement into Git history. Document the manual reprocess action as an explicit SQLite `DELETE FROM processed_messages WHERE message_id = ?` run only after inspecting the affected email; do not add an automatic retry against Kwork.

- [ ] **Step 4: Run CLI test, full test suite, and packaging check**

Run: `python -m pytest -v && python -m build`

Expected: PASS and a wheel/source distribution under `dist/`.

- [ ] **Step 5: Commit documentation and final validation**

```bash
git add README.md config.example.yaml tests/test_cli.py src/kwork_monitor/cli.py
git commit -m "docs: add Kwork monitor setup and operations guide"
```

## Plan Self-Review

- **Spec coverage:** IMAP-only source and no Kwork automation are enforced by Global Constraints, Tasks 2–3, and Task 6. Filtering, SQLite deduplication, proposal fallback, Telegram delivery, dry-run, error paths, secrets, and hourly cron each have implementation and test tasks.
- **Deliberate MVP boundary:** Email contents may omit part of the project brief; the implementation labels an incomplete draft and provides a manual project link rather than fetching that page.
- **Failure safety:** Telegram failure prevents state mutation and cursor movement; parse failures receive one alert then persist as `parse_error`; IMAP and configuration failures return non-zero for cron logs.
- **Type consistency:** `ProjectEmail`, `Settings`, `SecretSettings`, `DeliveryResult`, `StateStore`, `mail_key`, and `run_once` are introduced before consumers use them. No task refers to an undefined runtime component.
- **Placeholder scan:** No empty implementation markers, deferred work, or generic test instruction remains.
