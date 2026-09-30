# Kwork email monitor

This monitor reads Kwork project-notification emails over IMAP, filters them
locally, and sends a Telegram notification. It does not sign in to Kwork,
open project pages, submit proposals, or automatically retry against Kwork.

## Prepare Kwork and the mailbox

On the Kwork **Биржа** page, manually enable email notifications and select
only the rubrics relevant to your work. Use a dedicated mailbox and an app
password for IMAP; do not use your main mailbox password.

Copy `config.example.yaml` to `config.yaml` and adjust the IMAP host, mailbox,
senders, subject patterns, and keywords. Keep secrets in `.env`, never in
`config.yaml` or Git. The required variables are:

```dotenv
KWORK_IMAP_USERNAME=
KWORK_IMAP_PASSWORD=
KWORK_TELEGRAM_BOT_TOKEN=
KWORK_TELEGRAM_CHAT_ID=
KWORK_CODEASSIST_BASE_URL=
```

Edit `PROFILE.md` so it retains only claims that are accurate for you. The
monitor may use it to prepare a proposal draft; it must not invent experience,
prices, deadlines, or portfolio work.

## Manual server installation

Perform these commands manually on the server after reviewing the files and
providing the real values in its `.env` file:

```bash
cd /root/kwork-monitor
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
install -m 600 /dev/null /root/kwork-monitor/.env
install -m 600 config.example.yaml /root/kwork-monitor/config.yaml
install -m 600 PROFILE.example.md /root/kwork-monitor/PROFILE.md
.venv/bin/python -m kwork_monitor.cli --dry-run --fixture tests/fixtures/kwork_project_valid.eml
```

The fixture command uses no IMAP, Telegram, Code Assist credentials, or SQLite
state. It still parses and filters the local `.eml` message and reports what it
would notify. Use it as a local installation check.

Before scheduling anything, check the first real notification with a dry-run:

```bash
set -a && . ./.env && set +a
.venv/bin/python -m kwork_monitor.cli --config ./config.yaml --dry-run
```

Only after that succeeds and the notification content is correct, add this cron
line manually:

```cron
17 * * * * cd /root/kwork-monitor && set -a && . ./.env && set +a && ./.venv/bin/python -m kwork_monitor.cli --config ./config.yaml >> ./kwork-monitor.log 2>&1
```

The cron tick sends each relevant project with a **"Сгенерировать отклик"**
button instead of immediately using the generation bridge. Install the separate
long-polling daemon to process button clicks:

```bash
install -m 644 ops/kwork-monitor-bot.service /etc/systemd/system/kwork-monitor-bot.service
systemctl daemon-reload
systemctl enable --now kwork-monitor-bot
systemctl status kwork-monitor-bot --no-pager
```

Use `journalctl -u kwork-monitor-bot -f` to inspect the daemon. The manual
`--with-generation` override (`--config ./config.yaml --with-generation`) still
creates drafts immediately for all relevant projects in that tick and does not
create proposal buttons.

## Operations and recovery

If an app password or Telegram token leaks, revoke it and create a replacement,
then replace only the server `.env`. Do not put the replacement in Git history.

To manually reprocess one email, first inspect the affected email and identify
its message ID. Then run this explicit SQLite statement against the server
state database:

```sql
DELETE FROM processed_messages WHERE message_id = ?
```

Do not add an automatic retry against Kwork. Reprocessing is a deliberate
operator action after inspecting the email.

## Local verification

With Python 3.10+ and the test dependencies installed:

```bash
python -m pytest -v
python -m build
```
